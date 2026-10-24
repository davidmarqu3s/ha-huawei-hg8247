"""Exercise TLS against a real local server, including pre-request rejection."""
import asyncio
import importlib.util
from pathlib import Path
import ssl
import subprocess
import sys

import aiohttp
import pytest

spec = importlib.util.spec_from_file_location('tls_api', Path(__file__).parents[1] / 'custom_components/huawei_hg8247/api.py')
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)


def test_invalid_pin_rejected_before_requests():
    for pin in ['abc', 'g' * 64, '00' * 20]:
        with pytest.raises(api.HuaweiHG8247Error):
            api.HuaweiHG8247Client(None, '192.168.1.1', 'admin', 'secret', pin)


def test_verified_https_and_fail_closed(tmp_path):
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                    '-subj', '/CN=localhost', '-keyout', str(key), '-out', str(cert)],
                   check=True, capture_output=True)
    import hashlib
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()

    async def check():
        received = []
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        async def handle(reader, writer):
            headers = await reader.readuntil(b'\r\n\r\n')
            length = next((int(line.split(b':')[1]) for line in headers.split(b'\r\n')
                           if line.lower().startswith(b'content-length:')), 0)
            body = await reader.readexactly(length)
            received.append((headers, body))
            # A redirect must not cause a subsequent request.
            if b'/redirect ' in headers:
                writer.write(b'HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1/\r\nContent-Length: 0\r\n\r\n')
            else:
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok')
            await writer.drain()
            writer.close()
        server = await asyncio.start_server(handle, '127.0.0.1', 0, ssl=context)
        port = server.sockets[0].getsockname()[1]
        async with server, aiohttp.ClientSession() as session:
            # Use URL override solely to point test client to ephemeral local TLS port.
            client = api.HuaweiHG8247Client(session, '127.0.0.1', 'admin', 'secret', fingerprint)
            client._base = api.URL(f'https://127.0.0.1:{port}')
            assert await client._post('/login.cgi', {'PassWord': 'secret'}) == 'ok'
            assert len(received) == 1 and received[0][1] == b'PassWord=secret'
            client._ssl = aiohttp.Fingerprint(bytes(32))
            with pytest.raises(api.HuaweiHG8247Error, match='fingerprint does not match'):
                await client._post('/login.cgi', {'PassWord': 'secret'})
            assert len(received) == 1  # TLS handshake rejected before password transmission.
            client._ssl = True
            with pytest.raises(api.HuaweiHG8247Error):
                await client._post('/login.cgi', {'PassWord': 'secret'})
            assert len(received) == 1  # Unpinned self-signed cert also fails closed.
            client._ssl = aiohttp.Fingerprint(bytes.fromhex(fingerprint))
            with pytest.raises(api.HuaweiHG8247Error, match='redirect refused'):
                await client._post('/redirect')
            assert len(received) == 2
    asyncio.run(check())
