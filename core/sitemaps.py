from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.9
    changefreq = 'weekly'

    def items(self):
        return ['core:home', 'core:about', 'contact:contact']

    def location(self, item):
        return reverse(item)
