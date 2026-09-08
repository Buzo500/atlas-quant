"""HTTP-only probes of ATLAS on loopback, with deterministic resource cleanup."""
from contextlib import contextmanager
from http.client import HTTPConnection
from urllib.parse import urlsplit


@contextmanager
def open_local_http(url, *, timeout):
    target = urlsplit(url)
    if (target.scheme != "http" or target.hostname != "127.0.0.1"
            or target.username is not None or target.password is not None or target.fragment):
        raise ValueError("La comprobación requiere una URL HTTP local de ATLAS.")
    path = target.path or "/"
    if target.query:
        path += "?" + target.query

    # urllib.build_opener also builds HTTPS handlers for plain HTTP URLs. On
    # Python 3.14 that creates TLS contexts and opens an inherited SSLKEYLOGFILE
    # on every poll. Local probes need neither TLS nor environment proxies.
    connection = HTTPConnection("127.0.0.1", target.port, timeout=timeout)
    try:
        connection.request("GET", path)
        with connection.getresponse() as response:
            yield response
    finally:
        connection.close()
