from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ContactForm, DemoEnquiryForm, AdminLoginForm, StaffUserCreateForm
from .models import DemoEnquiry

User = get_user_model()


def staff_required(view_func):
    """Require an authenticated staff user."""
    return login_required(
        user_passes_test(lambda u: u.is_staff, login_url=settings.LOGIN_URL)(view_func)
    )


def superuser_required(view_func):
    """Require the primary admin (superuser)."""
    return login_required(
        user_passes_test(lambda u: u.is_superuser, login_url=settings.LOGIN_URL)(view_func)
    )


def contact(request):
    form = ContactForm()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save()
            try:
                send_mail(
                    subject=f'[SP-Tech Software Solution] New enquiry: {msg.get_subject_display()}',
                    message=(
                        f'Name: {msg.name}\n'
                        f'Email: {msg.email}\n'
                        f'Phone: {msg.phone}\n'
                        f'Company: {msg.company}\n\n'
                        f'{msg.message}'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass
            messages.success(request, 'Thank you! We will get back to you within 24 hours.')
            return redirect('contact:contact')

    context = {
        'meta_title': 'Contact Us – SP-Tech Software Solution | Get in Touch',
        'meta_description': (
            'Contact SP-Tech Software Solution for SanjivaniOne ERP demos, pricing enquiries, or technical '
            'support. We\'re here to help your business grow.'
        ),
        'meta_keywords': 'contact SP-Tech Software Solution, SanjivaniOne ERP demo, software demo request, business software support',
        'og_type': 'website',
        'form': form,
    }
    return render(request, 'contact/contact.html', context)


def book_demo(request):
    form = DemoEnquiryForm()
    if request.method == 'POST':
        form = DemoEnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save()
            try:
                send_mail(
                    subject=f'[SP-Tech Software Solution] New demo enquiry from {enquiry.full_name}',
                    message=(
                        f'Name: {enquiry.full_name}\n'
                        f'Email: {enquiry.email or "—"}\n'
                        f'Mobile: {enquiry.mobile_no}\n'
                        f'Company: {enquiry.company_name}\n'
                        f'Address: {enquiry.company_address}\n\n'
                        f'S/W Requirement:\n{enquiry.software_requirement}'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass
            messages.success(
                request,
                'Thank you! Your demo enquiry has been submitted. We will contact you shortly.',
            )
            return redirect('contact:book_demo')

    context = {
        'meta_title': 'Book a Demo – SP-Tech Software Solution',
        'meta_description': (
            'Book a free SanjivaniOne ERP demo from SP-Tech Software Solution. Tell us your software requirements '
            'and our team will get in touch.'
        ),
        'meta_keywords': 'book demo SanjivaniOne ERP, SP-Tech Software Solution, software demo request',
        'og_type': 'website',
        'form': form,
    }
    return render(request, 'contact/book_demo.html', context)


@require_http_methods(['GET', 'POST'])
def admin_login(request):
    if request.user.is_authenticated:
        return redirect(request.GET.get('next') or 'core:apps')

    form = AdminLoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        next_url = request.GET.get('next') or 'core:apps'
        return redirect(next_url)

    context = {
        'meta_title': 'Login – SP-Tech Software Solution',
        'meta_description': 'Sign in to open SP-Tech Software Solution apps.',
        'form': form,
        'robots': 'noindex, nofollow',
    }
    return render(request, 'contact/admin_login.html', context)


@login_required
def admin_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('core:home')


@staff_required
def enquiry_list(request):
    enquiries = DemoEnquiry.objects.all()
    unread_count = enquiries.filter(is_read=False).count()
    context = {
        'meta_title': 'Demo Enquiries – SP-Tech Software Solution Admin',
        'enquiries': enquiries,
        'unread_count': unread_count,
        'robots': 'noindex, nofollow',
    }
    return render(request, 'contact/enquiry_list.html', context)


@staff_required
def enquiry_detail(request, pk):
    enquiry = get_object_or_404(DemoEnquiry, pk=pk)
    if not enquiry.is_read:
        enquiry.is_read = True
        enquiry.save(update_fields=['is_read'])

    context = {
        'meta_title': f'Enquiry – {enquiry.full_name}',
        'enquiry': enquiry,
        'robots': 'noindex, nofollow',
    }
    return render(request, 'contact/enquiry_detail.html', context)


@superuser_required
def manage_users(request):
    form = StaffUserCreateForm()
    if request.method == 'POST':
        form = StaffUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'User "{user.username}" created. They can log in and open the Apps page.',
            )
            return redirect('contact:manage_users')

    users = User.objects.all().order_by('-is_superuser', 'username')
    context = {
        'meta_title': 'Manage Users – SP-Tech Software Solution Admin',
        'form': form,
        'users': users,
        'robots': 'noindex, nofollow',
    }
    return render(request, 'contact/manage_users.html', context)


@superuser_required
@require_POST
def toggle_user_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('contact:manage_users')
    if user.is_superuser:
        messages.error(request, 'Superuser accounts cannot be deactivated here.')
        return redirect('contact:manage_users')

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User "{user.username}" has been {status}.')
    return redirect('contact:manage_users')
