from django.contrib import admin
from .models import PortalApp, TeamMember, Testimonial


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'company', 'rating', 'is_active')
    list_editable = ('is_active',)


@admin.register(PortalApp)
class PortalAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'kind', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
