"""Local probes must not create TLS contexts or retain connections between polls."""
import errno
from http.client import HTTPException, IncompleteRead
import io
import json
import ssl
from types import SimpleNamespace

import pytest

import local_http
import run_atlas
import soak_atlas


HEALTH = b'{"status":"ok","live_available":false}'
URL = "http://127.0.0.1:8000/api/health"


class Response(io.BytesIO):
    def __init__(self, payload, status, read_error=None):
        super().__init__(payload)
        self.status = status
        self.read_error = read_error
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        if self.read_error is not None:
            raise self.read_error
        return super().read(size)


@pytest.fixture
def transport(monkeypatch):
    config = SimpleNamespace(payload=HEALTH, status=200, constructor_error=None,
                             request_error=None, response_error=None, read_error=None)
    connections = []

    class Connection:
        def __init__(self, host, port=None, *, timeout):
            if config.constructor_error is not None:
                raise config.constructor_error
            self.host, self.port, self.timeout = host, port, timeout
            self.requests = []
            self.close_calls = 0
            self.response = Response(config.payload, config.status, config.read_error)
            connections.append(self)

        def request(self, method, path):
            self.requests.append((method, path))
            if config.request_error is not None:
                raise config.request_error

        def getresponse(self):
            if config.response_error is not None:
                raise config.response_error
            return self.response

        def close(self):
            self.close_calls += 1

    monkeypatch.setattr(local_http, "HTTPConnection", Connection)
    return SimpleNamespace(config=config, connections=connections)


def test_local_response_and_connection_close_after_success(transport):
    with local_http.open_local_http(URL + "?probe=1", timeout=3) as response:
        assert json.load(response) == {"status": "ok", "live_available": False}
        assert not response.closed
    connection, = transport.connections
    assert (connection.host, connection.port, connection.timeout) == ("127.0.0.1", 8000, 3)
    assert connection.requests == [("GET", "/api/health?probe=1")]
    assert response.closed and connection.close_calls == 1


def test_repeated_health_and_monitor_probes_ignore_tls_keylog_and_proxies(transport, monkeypatch, tmp_path):
    # A missing parent would make TLS keylog initialization fail. The local
    # HTTP transport must never reach it, whatever the inherited environment.
    keylog = tmp_path / "not-created" / "keylog.txt"
    monkeypatch.setenv("SSLKEYLOGFILE", str(keylog))
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, "http://proxy.invalid:1")

    def forbidden_tls(*args, **kwargs):
        pytest.fail("An HTTP loopback probe must not create a TLS context")

    monkeypatch.setattr(ssl, "_create_default_https_context", forbidden_tls)
    monkeypatch.setattr(ssl, "create_default_context", forbidden_tls)
    for _ in range(100):
        assert run_atlas.health(8000) is True
        payload, elapsed = soak_atlas.http_read(URL, json_response=True)
        assert payload == {"status": "ok", "live_available": False}
        assert elapsed >= 0
    assert len(transport.connections) == 200
    assert all(c.close_calls == 1 and c.response.closed for c in transport.connections)
    assert not keylog.exists()


@pytest.mark.parametrize("phase", ["request", "response", "read", "caller"])
def test_connection_closes_when_request_response_read_or_caller_fails(transport, phase):
    failure = RuntimeError("deliberate probe failure")
    if phase != "caller":
        setattr(transport.config, f"{phase}_error", failure)
    with pytest.raises(RuntimeError, match="deliberate probe failure"):
        with local_http.open_local_http(URL, timeout=2) as response:
            if phase == "caller":
                raise failure
            response.read()
    connection, = transport.connections
    assert connection.close_calls == 1
    if phase in {"read", "caller"}:
        assert connection.response.closed


@pytest.mark.parametrize("phase, failure", [
    ("constructor", OSError(errno.EMFILE, "Too many open files")),
    ("request", TimeoutError("timed out")),
    ("response", HTTPException("bad response")),
    ("read", IncompleteRead(b"{")),
])
def test_health_transport_failures_return_false_including_descriptor_exhaustion(transport, phase, failure):
    setattr(transport.config, f"{phase}_error", failure)
    assert run_atlas.health(8000) is False
    assert all(c.close_calls == 1 for c in transport.connections)
    if phase == "read":
        assert transport.connections[0].response.closed


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b"null", b'{"status":"ok","live_available":true}'])
def test_health_rejects_invalid_json_shape_and_unsafe_status(transport, payload):
    transport.config.payload = payload
    assert run_atlas.health(8000) is False
    connection, = transport.connections
    assert connection.close_calls == 1 and connection.response.closed


@pytest.mark.parametrize("status", [301, 302, 503])
def test_health_and_monitor_reject_http_errors_without_following_redirects(transport, status):
    transport.config.status = status
    assert run_atlas.health(8000) is False
    with pytest.raises(RuntimeError, match="HTTP"):
        soak_atlas.http_read(URL, json_response=True)
    assert len(transport.connections) == 2
    assert all(len(c.requests) == 1 and c.close_calls == 1 and c.response.closed
               for c in transport.connections)


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:8000/api/health",
    "http://example.invalid/api/health",
    "http://localhost:8000/api/health",
    "http://127.0.0.1.example.invalid:8000/api/health",
    "http://user:password@127.0.0.1:8000/api/health",
    "http://127.0.0.1:8000/api/health#fragment",
])
def test_nonliteral_loopback_http_urls_are_rejected_before_connecting(transport, url):
    with pytest.raises(ValueError, match="HTTP local"):
        with local_http.open_local_http(url, timeout=2):
            pytest.fail("Invalid local URL was accepted")
    assert not transport.connections


@pytest.mark.parametrize("extra", [0, 1])
def test_monitor_preserves_eight_mib_response_limit_and_closes_both_resources(transport, extra):
    limit = 8 * 1024**2
    transport.config.payload = b"x" * (limit + extra)
    if extra:
        with pytest.raises(RuntimeError, match="excesiva"):
            soak_atlas.http_read(URL)
    else:
        payload, _ = soak_atlas.http_read(URL)
        assert len(payload) == limit
    connection, = transport.connections
    assert connection.response.read_sizes == [limit + 1]
    assert connection.close_calls == 1 and connection.response.closed


def test_monitor_invalid_json_still_closes_response_and_connection(transport):
    transport.config.payload = b"not-json"
    with pytest.raises(json.JSONDecodeError):
        soak_atlas.http_read(URL, json_response=True)
    connection, = transport.connections
    assert connection.close_calls == 1 and connection.response.closed
