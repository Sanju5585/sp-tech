from django.contrib import admin
from .models import ContactMessage, DemoEnquiry


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'company', 'created_at', 'is_read')
    list_filter = ('subject', 'is_read')
    search_fields = ('name', 'email', 'company', 'message')
    readonly_fields = ('name', 'email', 'phone', 'company', 'subject', 'message', 'created_at')
    list_editable = ('is_read',)


@admin.register(DemoEnquiry)
class DemoEnquiryAdmin(admin.ModelAdmin):
    list_display = (
        'full_name_display',
        'company_name',
        'mobile_no',
        'created_at',
        'is_read',
    )
    list_filter = ('is_read', 'created_at')
    search_fields = (
        'first_name',
        'surname',
        'email',
        'company_name',
        'mobile_no',
        'software_requirement',
    )
    readonly_fields = (
        'first_name',
        'surname',
        'email',
        'company_name',
        'company_address',
        'mobile_no',
        'software_requirement',
        'created_at',
    )
    list_editable = ('is_read',)

    @admin.display(description='Name', ordering='first_name')
    def full_name_display(self, obj):
        return obj.full_name
