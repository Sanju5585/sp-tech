from django.conf import settings


def seo_defaults(request):
    """Inject site-wide SEO and branding defaults into every template."""
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'SP-Tech Software Solution'),
        'SITE_URL': getattr(settings, 'SITE_URL', ''),
        'SITE_TAGLINE': getattr(settings, 'SITE_TAGLINE', ''),
        'SITE_DESCRIPTION': getattr(settings, 'SITE_DESCRIPTION', ''),
        'WHATSAPP_NUMBER': getattr(settings, 'WHATSAPP_NUMBER', '918447695372'),
    }
