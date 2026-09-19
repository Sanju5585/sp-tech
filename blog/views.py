import json
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator

from .models import Post, Tag


def post_list(request):
    posts = Post.objects.filter(status=Post.STATUS_PUBLISHED).select_related('author')
    tag_slug = request.GET.get('tag')
    current_tag = None
    if tag_slug:
        current_tag = get_object_or_404(Tag, slug=tag_slug)
        posts = posts.filter(tags=current_tag)

    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'meta_title': 'Blog – SP-Tech Software Solution | Business Automation, AI & SMB Software Trends',
        'meta_description': (
            'Read SP-Tech Software Solution insights on SanjivaniOne ERP, business automation, AI for SMBs, '
            'and software trends that help small and medium businesses grow.'
        ),
        'meta_keywords': (
            'business automation blog, AI for SMBs, SMB software trends, '
            'logistics software articles'
        ),
        'og_type': 'website',
        'page_obj': page_obj,
        'tags': Tag.objects.all(),
        'current_tag': current_tag,
    }
    return render(request, 'blog/post_list.html', context)


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status=Post.STATUS_PUBLISHED)
    schema_markup = json.dumps(post.get_schema_markup(), indent=2)
    context = {
        'meta_title': post.meta_title or f'{post.title} – SP-Tech Software Solution Blog',
        'meta_description': post.meta_description or post.excerpt[:155],
        'meta_keywords': post.meta_keywords,
        'og_type': 'article',
        'og_image': post.featured_image.url if post.featured_image else '',
        'post': post,
        'schema_markup': schema_markup,
    }
    return render(request, 'blog/post_detail.html', context)
