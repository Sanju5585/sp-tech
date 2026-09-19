from django.db import models


class ContactMessage(models.Model):
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('demo', 'Request a Demo'),
        ('support', 'Technical Support'),
        ('partnership', 'Partnership'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=150, blank=True)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} – {self.get_subject_display()} ({self.created_at:%d %b %Y})'


class DemoEnquiry(models.Model):
    first_name = models.CharField('Name', max_length=100)
    surname = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    company_name = models.CharField(max_length=200)
    company_address = models.TextField()
    mobile_no = models.CharField('Mobile No', max_length=20)
    software_requirement = models.TextField('S/W Requirement')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Demo Enquiry'
        verbose_name_plural = 'Demo Enquiries'

    def __str__(self):
        return f'{self.first_name} {self.surname} – {self.company_name} ({self.created_at:%d %b %Y})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.surname}'.strip()
