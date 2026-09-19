from django import forms

from .models import PortalApp


class PortalAppForm(forms.ModelForm):
    class Meta:
        model = PortalApp
        fields = ['name', 'slug', 'tagline', 'description', 'icon_class', 'kind', 'external_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'App name'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'school-timetable'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short line'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon_class': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-calendar3'}),
            'kind': forms.Select(attrs={'class': 'form-select'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://…'}),
        }
