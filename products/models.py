from django.db import models
from django.urls import reverse


class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Product Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, help_text='SEO-friendly URL segment, e.g. logistics-management-software')
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    tagline = models.CharField(max_length=300)
    short_description = models.TextField(help_text='Shown on product listing cards')
    full_description = models.TextField(help_text='Full marketing copy for the detail page')
    icon_class = models.CharField(max_length=60, default='bi-box-seam', help_text='Bootstrap icon class')
    hero_image = models.ImageField(upload_to='products/', blank=True, null=True)
    demo_url = models.URLField(blank=True, help_text='Live demo link (optional)')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    # SEO fields
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:detail', kwargs={'slug': self.slug})

    def get_schema_markup(self):
        """Return JSON-LD schema.org SoftwareApplication markup."""
        return {
            '@context': 'https://schema.org',
            '@type': 'SoftwareApplication',
            'name': self.name,
            'description': self.short_description,
            'applicationCategory': 'BusinessApplication',
            'operatingSystem': 'Web',
            'offers': {
                '@type': 'Offer',
                'availability': 'https://schema.org/InStock',
                'priceCurrency': 'INR',
            },
            'provider': {
                '@type': 'Organization',
                'name': 'SP-Tech Software Solution',
                'url': 'https://www.sanjivani.com',
                'logo': 'https://www.sanjivani.com/static/assets/sp-tech-logo.png',
            },
        }


class ProductFeature(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='features')
    title = models.CharField(max_length=150)
    description = models.TextField()
    icon_class = models.CharField(max_length=60, default='bi-check-circle-fill')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.product.name} – {self.title}'


class ProductScreenshot(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='screenshots')
    image = models.ImageField(upload_to='products/screenshots/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.product.name} screenshot #{self.order}'
