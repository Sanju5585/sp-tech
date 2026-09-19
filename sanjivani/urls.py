from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from core.sitemaps import StaticViewSitemap
from products.sitemaps import ProductSitemap
from blog.sitemaps import BlogSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
    'blog': BlogSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    # Fixed paths before product slug catch-all
    path('blog/', include('blog.urls')),
    path('contact/', include('contact.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    # Product list + SEO slug detail (must be last — catches /<slug>/)
    path('', include('products.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
