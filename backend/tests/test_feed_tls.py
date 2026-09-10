"""Trust selection and atomic local bundle generation; no network or private keys."""
from pathlib import Path
import certifi
import pytest
from atlas_quant import feed_tls


def clear_configuration(monkeypatch):
    for name in ('REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE','SSL_CERT_FILE'):
        monkeypatch.delenv(name, raising=False)


def test_windows_adds_only_existing_server_trust_and_keeps_certifi(tmp_path,monkeypatch):
    clear_configuration(monkeypatch)
    base=tmp_path/'certifi.pem'
    base.write_text('PUBLIC CERTIFI FIXTURE\n',encoding='ascii')
    monkeypatch.setattr(certifi,'where',lambda:str(base))
    enumerations=[]
    def certificates(store):
        enumerations.append(store)
        return [(b'public-root','x509_asn',True),(b'public-server','x509_asn',{feed_tls.ssl.Purpose.SERVER_AUTH.oid}),
                (b'client-only','x509_asn',{feed_tls.ssl.Purpose.CLIENT_AUTH.oid}),(b'unsupported','pkcs_7_asn',True)]
    monkeypatch.setattr(feed_tls.ssl,'enum_certificates',certificates,raising=False)
    target=Path(feed_tls.ca_bundle(tmp_path/'cache'))
    content=target.read_text(encoding='ascii')
    assert content.startswith('PUBLIC CERTIFI FIXTURE')
    assert feed_tls.ssl.DER_cert_to_PEM_cert(b'public-root') in content
    assert feed_tls.ssl.DER_cert_to_PEM_cert(b'client-only') not in content
    assert content.count('BEGIN CERTIFICATE')==2
    stamp=target.stat().st_mtime_ns
    assert feed_tls.ca_bundle(tmp_path/'cache')==str(target)
    assert target.stat().st_mtime_ns==stamp
    assert enumerations==['ROOT','CA','ROOT','CA']


def test_explicit_ca_configuration_is_preserved_and_missing_file_fails(tmp_path,monkeypatch):
    clear_configuration(monkeypatch)
    bundle=tmp_path/'custom.pem'
    bundle.write_text('PUBLIC CUSTOM CA',encoding='ascii')
    monkeypatch.setenv('REQUESTS_CA_BUNDLE',str(bundle))
    assert feed_tls.ca_bundle(tmp_path/'cache')==str(bundle.resolve())
    assert not (tmp_path/'cache').exists()
    monkeypatch.setenv('REQUESTS_CA_BUNDLE',str(tmp_path/'missing.pem'))
    with pytest.raises(OSError):feed_tls.ca_bundle(tmp_path/'cache')


def test_other_platform_keeps_verification_enabled(tmp_path,monkeypatch):
    clear_configuration(monkeypatch)
    monkeypatch.delattr(feed_tls.ssl,'enum_certificates',raising=False)
    assert feed_tls.ca_bundle(tmp_path) is True
