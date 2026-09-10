"""Use explicitly configured CAs or Windows' existing server trust for Yahoo.

No certificate is downloaded or installed. The generated bundle contains only
public certificates; peer and hostname verification remain enabled by curl.
"""
import os
from pathlib import Path
import ssl
from uuid import uuid4


def ca_bundle(directory):
    configured = next((os.environ[k] for k in ('REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'SSL_CERT_FILE') if os.environ.get(k)), None)
    if configured:
        target = Path(configured).expanduser().resolve()
        if not target.is_file():
            raise OSError('El archivo de CA configurado no existe.')
        return str(target)
    if not hasattr(ssl, 'enum_certificates'):
        return True
    import certifi
    certificates = set()
    for store in ('ROOT', 'CA'):
        for value, encoding, trust in ssl.enum_certificates(store):
            if encoding == 'x509_asn' and (trust is True or ssl.Purpose.SERVER_AUTH.oid in trust):
                certificates.add(ssl.DER_cert_to_PEM_cert(value))
    content = Path(certifi.where()).read_text(encoding='ascii') + '\n' + ''.join(sorted(certificates))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'windows-server-ca.pem'
    if not target.exists() or target.read_text(encoding='ascii') != content:
        temporary = directory / ('ca-' + uuid4().hex + '.tmp')
        try:
            temporary.write_text(content, encoding='ascii')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return str(target.resolve())
