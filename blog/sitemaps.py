from django.contrib.sitemaps import Sitemap
from .models import Post


class BlogSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Post.objects.filter(status=Post.STATUS_PUBLISHED)

    def lastmod(self, obj):
        return obj.updated_at
