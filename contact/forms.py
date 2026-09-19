from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import ContactMessage, DemoEnquiry

User = get_user_model()


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'company', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 84476 95372'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name (optional)'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Tell us how we can help you…',
            }),
        }


class DemoEnquiryForm(forms.ModelForm):
    class Meta:
        model = DemoEnquiry
        fields = [
            'first_name',
            'surname',
            'email',
            'company_name',
            'company_address',
            'mobile_no',
            'software_requirement',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name',
                'autocomplete': 'given-name',
            }),
            'surname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Surname',
                'autocomplete': 'family-name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'you@company.com (optional)',
                'autocomplete': 'email',
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company name',
                'autocomplete': 'organization',
            }),
            'company_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Company address',
                'autocomplete': 'street-address',
            }),
            'mobile_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10-digit mobile number',
                'autocomplete': 'tel',
                'inputmode': 'tel',
            }),
            'software_requirement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Which software do you need? e.g. Accounting, Payroll, Logistics…',
            }),
        }

    def clean_mobile_no(self):
        mobile = self.cleaned_data['mobile_no'].strip().replace(' ', '')
        digits = ''.join(c for c in mobile if c.isdigit())
        if mobile.startswith('+91'):
            digits = digits[-10:] if len(digits) >= 10 else digits
        elif mobile.startswith('91') and len(digits) == 12:
            digits = digits[-10:]
        if len(digits) != 10:
            raise forms.ValidationError('Enter a valid 10-digit mobile number.')
        return digits


class AdminLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })
    )


class StaffUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'new-password',
        }),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
                'autocomplete': 'off',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@company.com',
            }),
        }

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_staff = False
        user.is_active = True
        user.is_superuser = False
        if commit:
            user.save()
        return user
