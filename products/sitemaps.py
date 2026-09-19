from django.contrib.sitemaps import Sitemap
from .models import Product


class ProductSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at
