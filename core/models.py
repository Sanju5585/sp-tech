from django.db import models


class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='team/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    linkedin_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.name} – {self.designation}'


class Testimonial(models.Model):
    client_name = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.client_name} ({self.company})'


class PortalApp(models.Model):
    KIND_INTERNAL = 'internal'
    KIND_EXTERNAL = 'external'
    KIND_CHOICES = (
        (KIND_INTERNAL, 'Open inside site'),
        (KIND_EXTERNAL, 'Open link'),
    )

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=60, default='bi-grid-fill')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_INTERNAL)
    external_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
