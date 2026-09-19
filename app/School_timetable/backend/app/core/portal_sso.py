import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode

from app.config import get_settings


def verify_portal_sso_token(token: str) -> dict | None:
    settings = get_settings()
    secret = (settings.portal_sso_secret or settings.secret_key).encode("utf-8")
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    pad = "=" * (-len(body) % 4)
    try:
        data = json.loads(urlsafe_b64decode(body + pad).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(data.get("exp", 0)) < int(time.time()):
        return None
    return data
