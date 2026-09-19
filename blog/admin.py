from django.contrib import admin
from .models import Post, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'published_at')
    list_filter = ('status', 'tags')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    ordering = ['-published_at']
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'author', 'featured_image', 'excerpt', 'content', 'tags', 'status', 'published_at')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
