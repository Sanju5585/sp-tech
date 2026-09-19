"""
WSGI config for SP-Tech Software Solution project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanjivani.settings')
application = get_wsgi_application()
