from mimetypes import guess_type
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.vary import vary_on_headers

from products.models import Product
from .forms import PortalAppForm
from .models import PortalApp, TeamMember, Testimonial
from .sso import make_portal_sso_token


def _ensure_default_apps():
    PortalApp.objects.get_or_create(
        slug='school-timetable',
        defaults={
            'name': 'School Timetable',
            'tagline': 'Generate conflict-free weekly school timetables',
            'description': (
                'OR-Tools builds class, teacher and room grids. Open it from here — '
                'you are already signed in.'
            ),
            'icon_class': 'bi-calendar3',
            'kind': PortalApp.KIND_INTERNAL,
            'is_active': True,
            'order': 0,
        },
    )


@vary_on_headers('Cookie')
def home(request):
    flagship = Product.objects.filter(slug='sanjivanione-erp', is_active=True).first()
    featured_products = Product.objects.filter(is_active=True)
    if flagship:
        featured_products = featured_products.exclude(pk=flagship.pk)[:3]
    else:
        featured_products = featured_products.filter(is_featured=True)[:3]
    testimonials = Testimonial.objects.filter(is_active=True)[:4]
    context = {
        'meta_title': 'SP-Tech Software Solution – SanjivaniOne ERP for SMB Growth',
        'meta_description': (
            'SP-Tech Software Solution builds SanjivaniOne ERP, our flagship platform for '
            'finance, inventory, HR, sales, and operations—plus supporting tools that help '
            'small and medium businesses replace outdated systems and grow faster.'
        ),
        'meta_keywords': (
            'SP-Tech Software Solution, SanjivaniOne ERP, SMB software, logistics management, '
            'sales management system, AI for SMBs, business automation India'
        ),
        'og_type': 'website',
        'flagship': flagship,
        'featured_products': featured_products,
        'testimonials': testimonials,
    }
    return render(request, 'core/home.html', context)


@vary_on_headers('Cookie')
def about(request):
    team = TeamMember.objects.filter(is_active=True)
    context = {
        'meta_title': 'About Us – SP-Tech Software Solution | Makers of SanjivaniOne ERP',
        'meta_description': (
            'Founded in 2024, SP-Tech Software Solution builds SanjivaniOne ERP and supporting '
            'business software so SMBs become profitable with fast, AI-enabled tools and on-call support.'
        ),
        'meta_keywords': (
            'about SP-Tech Software Solution, SanjivaniOne ERP, SMB software company, '
            'AI for small business, business software India'
        ),
        'og_type': 'website',
        'team': team,
    }
    return render(request, 'core/about.html', context)


@login_required
@never_cache
def apps_page(request):
    _ensure_default_apps()
    form = None
    if request.user.is_superuser:
        form = PortalAppForm()
        if request.method == 'POST':
            form = PortalAppForm(request.POST)
            if form.is_valid():
                app = form.save(commit=False)
                app.is_active = True
                app.save()
                return redirect('core:apps')
    apps = PortalApp.objects.filter(is_active=True)
    context = {
        'meta_title': 'Apps – SP-Tech Software Solution',
        'meta_description': 'Open SP-Tech Software Solution applications from your workspace.',
        'robots': 'noindex, nofollow',
        'apps': apps,
        'form': form,
    }
    return render(request, 'core/apps.html', context)


@login_required
@never_cache
def launch_app(request, slug):
    app = get_object_or_404(PortalApp, slug=slug, is_active=True)
    if app.kind == PortalApp.KIND_EXTERNAL and app.external_url:
        return redirect(app.external_url)
    token = make_portal_sso_token(request.user.username, request.user.is_superuser)
    spa_base = reverse('core:timetable_spa')
    launch_url = f'{spa_base}?sso={token}'
    context = {
        'meta_title': f'{app.name} – SP-Tech Software Solution',
        'robots': 'noindex, nofollow',
        'app': app,
        'launch_url': launch_url,
        'spa_ready': Path(settings.TIMETABLE_SPA_DIR, 'index.html').is_file(),
    }
    return render(request, 'core/app_launch.html', context)


def _spa_root() -> Path:
    root = Path(settings.TIMETABLE_SPA_DIR)
    collected = Path(settings.STATIC_ROOT) / 'timetable-app'
    if (root / 'index.html').is_file():
        return root
    return collected


@login_required
@never_cache
def timetable_spa(request, rest=''):
    root = _spa_root().resolve()
    if rest:
        candidate = (root / rest).resolve()
        if str(candidate).startswith(str(root)) and candidate.is_file():
            content_type = guess_type(str(candidate))[0] or 'application/octet-stream'
            return FileResponse(candidate.open('rb'), content_type=content_type)
    index = root / 'index.html'
    if not index.is_file():
        return render(request, 'core/app_unavailable.html', status=503)
    return FileResponse(index.open('rb'), content_type='text/html')


@csrf_exempt
@login_required
def timetable_api_proxy(request, path):
    target = f"{settings.TIMETABLE_API_URL.rstrip('/')}/api/{path.lstrip('/')}"
    qs = request.META.get('QUERY_STRING')
    if qs:
        target = f'{target}?{qs}'
    headers = {}
    for name in ('Authorization', 'X-School-Id', 'Content-Type', 'Accept'):
        value = request.headers.get(name)
        if value:
            headers[name] = value
    body = request.body if request.method in {'POST', 'PUT', 'PATCH'} else None
    req = Request(target, data=body, headers=headers, method=request.method)
    try:
        with urlopen(req, timeout=120) as resp:
            payload = resp.read()
            response = HttpResponse(payload, status=resp.status, content_type=resp.headers.get('Content-Type'))
            disposition = resp.headers.get('Content-Disposition')
            if disposition:
                response['Content-Disposition'] = disposition
            return response
    except HTTPError as exc:
        return HttpResponse(
            exc.read(),
            status=exc.code,
            content_type=exc.headers.get('Content-Type', 'application/json'),
        )
    except URLError:
        return JsonResponse({'detail': 'Timetable service is not running.'}, status=503)
