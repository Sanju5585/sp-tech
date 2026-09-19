"""
ASGI config for SP-Tech Software Solution project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanjivani.settings')
application = get_asgi_application()
