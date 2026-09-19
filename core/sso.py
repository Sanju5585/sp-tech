import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from django.conf import settings


def _secret() -> bytes:
    return (getattr(settings, 'PORTAL_SSO_SECRET', '') or settings.SECRET_KEY).encode('utf-8')


def make_portal_sso_token(username: str, is_superuser: bool = False, ttl: int = 180) -> str:
    payload = json.dumps(
        {
            'u': username,
            'su': bool(is_superuser),
            'exp': int(time.time()) + ttl,
        },
        separators=(',', ':'),
    ).encode('utf-8')
    body = urlsafe_b64encode(payload).rstrip(b'=').decode('ascii')
    sig = hmac.new(_secret(), body.encode('ascii'), hashlib.sha256).hexdigest()
    return f'{body}.{sig}'


def verify_portal_sso_token(token: str) -> dict | None:
    try:
        body, sig = token.split('.', 1)
    except ValueError:
        return None
    expected = hmac.new(_secret(), body.encode('ascii'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    pad = '=' * (-len(body) % 4)
    try:
        data = json.loads(urlsafe_b64decode(body + pad).decode('utf-8'))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(data.get('exp', 0)) < int(time.time()):
        return None
    return data
