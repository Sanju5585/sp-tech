import json
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import cache_page

from .models import Product, ProductCategory


@cache_page(60 * 15)
def product_list(request):
    products = Product.objects.filter(is_active=True).prefetch_related('features')
    categories = ProductCategory.objects.all()
    context = {
        'meta_title': 'Software Products – SP-Tech Software Solution | SanjivaniOne ERP',
        'meta_description': (
            'Explore SanjivaniOne ERP, the flagship product of SP-Tech Software Solution, '
            'plus logistics, sales, accounting, and other tools to grow your business.'
        ),
        'meta_keywords': 'SanjivaniOne ERP, SP-Tech Software Solution, logistics software, sales management system, business tools',
        'og_type': 'website',
        'products': products,
        'categories': categories,
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    schema_markup = json.dumps(product.get_schema_markup(), indent=2)
    related_products = (
        Product.objects.filter(is_active=True)
        .exclude(pk=product.pk)[:3]
    )
    context = {
        'meta_title': product.meta_title or f'{product.name} – SP-Tech Software Solution',
        'meta_description': product.meta_description or product.short_description[:155],
        'meta_keywords': product.meta_keywords,
        'og_type': 'product',
        'og_image': product.hero_image.url if product.hero_image else '',
        'product': product,
        'schema_markup': schema_markup,
        'related_products': related_products,
    }
    return render(request, 'products/product_detail.html', context)
