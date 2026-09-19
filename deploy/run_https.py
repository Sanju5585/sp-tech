"""
Run SP-Tech Software Solution on ports 80 (HTTP→HTTPS redirect) and 443 (HTTPS).

Architecture:
  Browser → :80  (redirect to HTTPS)
  Browser → :443 (SSL terminator) → Waitress WSGI on 127.0.0.1:8000

Requires Administrator privileges on Windows to bind ports 80/443.

Usage (from project root, as Administrator):
    .\\venv\\Scripts\\python.exe deploy\\run_https.py
"""
from __future__ import annotations

import os
import ssl
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.request import Request
from urllib.error import HTTPError, URLError

# Project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanjivani.settings')

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

CERT_FILE = Path(os.getenv('SSL_CERT_FILE', Path(__file__).resolve().parent / 'certs' / 'cert.pem'))
KEY_FILE = Path(os.getenv('SSL_KEY_FILE', Path(__file__).resolve().parent / 'certs' / 'key.pem'))

INTERNAL_HOST = '127.0.0.1'
INTERNAL_PORT = int(os.getenv('INTERNAL_WSGI_PORT', '8000'))
HTTP_PORT = int(os.getenv('HTTP_PORT', '80'))
HTTPS_PORT = int(os.getenv('HTTPS_PORT', '443'))
SSL_DOMAINS = [
    d.strip()
    for d in os.getenv(
        'SSL_DOMAINS',
        'sanjivani.com,www.sanjivani.com,localhost,127.0.0.1',
    ).split(',')
    if d.strip()
]


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._redirect()

    def do_POST(self):
        self._redirect()

    def do_HEAD(self):
        self._redirect()

    def _redirect(self):
        host = self.headers.get('Host', 'localhost').split(':')[0]
        loc = f'https://{host}{self.path}'
        self.send_response(301)
        self.send_header('Location', loc)
        self.end_headers()

    def log_message(self, fmt, *args):
        sys.stdout.write(f'[http:{HTTP_PORT}] {self.address_string()} {fmt % args}\n')


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    def _proxy(self):
        url = f'http://{INTERNAL_HOST}:{INTERNAL_PORT}{self.path}'
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else None

        headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in {'host', 'connection', 'transfer-encoding', 'content-length'}
        }
        host = self.headers.get('Host', 'localhost')
        headers['Host'] = host
        headers['X-Forwarded-Proto'] = 'https'
        headers['X-Forwarded-Host'] = host
        headers['X-Forwarded-For'] = self.client_address[0]
        headers['Accept-Encoding'] = 'identity'

        req = Request(url, data=body, headers=headers, method=self.command)
        opener = urllib.request.build_opener(self._NoRedirect)
        try:
            with opener.open(req, timeout=90) as resp:
                self._write_upstream(resp.status, resp.headers, resp.read())
        except HTTPError as exc:
            self._write_upstream(exc.code, exc.headers, exc.read())
        except URLError as exc:
            msg = f'Upstream error: {exc}'.encode()
            self.send_response(502)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def _write_upstream(self, status, headers, data: bytes):
        self.send_response(status)
        for key, val in headers.items():
            if key.lower() in {
                'transfer-encoding', 'connection', 'content-encoding',
                'content-length', 'keep-alive',
            }:
                continue
            self.send_header(key, val)
        self.send_header('Content-Length', str(len(data or b'')))
        self.send_header('Connection', 'close')
        self.end_headers()
        if data and self.command != 'HEAD':
            self.wfile.write(data)

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def do_PATCH(self):
        self._proxy()

    def do_HEAD(self):
        self._proxy()

    def do_OPTIONS(self):
        self._proxy()

    def log_message(self, fmt, *args):
        sys.stdout.write(f'[https:{HTTPS_PORT}] {self.address_string()} {fmt % args}\n')


def ensure_certs() -> None:
    if CERT_FILE.exists() and KEY_FILE.exists():
        return
    print('SSL certs not found - generating certificate for production domains...')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_ssl_cert import generate
    generate(SSL_DOMAINS or ['localhost', '127.0.0.1'])


def start_waitress() -> None:
    import django
    django.setup()
    from waitress import serve
    from sanjivani.wsgi import application

    print(f'[wsgi] Waitress listening on http://{INTERNAL_HOST}:{INTERNAL_PORT}')
    serve(
        application,
        host=INTERNAL_HOST,
        port=INTERNAL_PORT,
        threads=8,
        channel_timeout=120,
        url_scheme='https',
        trusted_proxy='127.0.0.1',
        trusted_proxy_count=1,
        trusted_proxy_headers={'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host'},
    )


def start_http_redirect() -> None:
    server = ThreadingHTTPServer(('0.0.0.0', HTTP_PORT), RedirectHandler)
    print(f'[http] Redirect server on http://0.0.0.0:{HTTP_PORT} -> HTTPS')
    server.serve_forever()


def start_https_proxy() -> None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))

    server = ThreadingHTTPServer(('0.0.0.0', HTTPS_PORT), ProxyHandler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f'[https] SSL server on https://0.0.0.0:{HTTPS_PORT}')
    print('Open: https://www.sanjivani.com/  or  https://sanjivani.com/')
    print('Local: https://127.0.0.1/  (browser will warn on a self-signed cert)')
    server.serve_forever()


def main() -> None:
    # Avoid Windows console Unicode crashes
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    ensure_certs()

    # Collect static so WhiteNoise can serve assets
    os.chdir(ROOT)
    try:
        from django.core.management import call_command
        import django
        django.setup()
        call_command('collectstatic', '--noinput', '--clear', verbosity=0)
    except Exception as exc:
        print(f'Warning: collectstatic skipped ({exc})')

    threading.Thread(target=start_waitress, name='waitress', daemon=True).start()
    threading.Thread(target=start_http_redirect, name='http-redirect', daemon=True).start()

    try:
        start_https_proxy()
    except PermissionError:
        print('\nERROR: Permission denied binding to ports 80/443.')
        print('On Windows, run PowerShell as Administrator:')
        print(r'  .\deploy\start_https.ps1')
        sys.exit(1)
    except OSError as exc:
        print(f'\nERROR: Could not bind ports - {exc}')
        print('Another app (IIS, Skype, Apache) may already be using 80/443.')
        sys.exit(1)


if __name__ == '__main__':
    main()
