from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class Tag(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
    ]

    title = models.CharField(max_length=250)
    slug = models.SlugField(unique=True, max_length=250)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blog_posts')
    featured_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    excerpt = models.TextField(max_length=350, help_text='Short summary shown on listing page')
    content = models.TextField()
    tags = models.ManyToManyField(Tag, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # SEO
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:detail', kwargs={'slug': self.slug})

    def get_schema_markup(self):
        return {
            '@context': 'https://schema.org',
            '@type': 'BlogPosting',
            'headline': self.title,
            'description': self.excerpt,
            'datePublished': self.published_at.isoformat(),
            'dateModified': self.updated_at.isoformat(),
            'author': {
                '@type': 'Person',
                'name': self.author.get_full_name() if self.author else 'SP-Tech Software Solution Team',
            },
            'publisher': {
                '@type': 'Organization',
                'name': 'SP-Tech Software Solution',
                'logo': {
                    '@type': 'ImageObject',
                    'url': 'https://www.sanjivani.com/static/assets/sp-tech-logo.png',
                },
            },
        }
