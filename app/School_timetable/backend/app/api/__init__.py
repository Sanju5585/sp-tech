from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.ai import router as ai_router

# Additional per-route limits applied in main via SlowAPI default.
# Explicit decorators live here if imported by tests.

limiter = Limiter(key_func=get_remote_address)


def apply_ai_limits():
    for route in ai_router.routes:
        if hasattr(route, "endpoint"):
            route.endpoint = limiter.limit("20/minute")(route.endpoint)
