from django.contrib import admin
from .models import Product, ProductCategory, ProductFeature, ProductScreenshot


class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 3


class ProductScreenshotInline(admin.TabularInline):
    model = ProductScreenshot
    extra = 2


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'is_featured', 'is_active', 'order')
    list_editable = ('is_featured', 'is_active', 'order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'tagline', 'short_description')
    fieldsets = (
        ('Product Info', {
            'fields': ('name', 'slug', 'category', 'tagline', 'short_description',
                       'full_description', 'icon_class', 'hero_image', 'demo_url',
                       'is_featured', 'is_active', 'order')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
    )
    inlines = [ProductFeatureInline, ProductScreenshotInline]


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
