from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

USERNAME = 'superAdmin'
PASSWORD = 'sanjeev@5585'
EMAIL = 'superadmin@sanjivani.app'


class Command(BaseCommand):
    help = 'Create or reset the site super admin (superAdmin).'

    def handle(self, *args, **options):
        user = User.objects.filter(username__iexact=USERNAME).first()
        if user is None:
            user = User.objects.filter(is_superuser=True).order_by('id').first()
        if user is None:
            User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
            self.stdout.write(self.style.SUCCESS(f'Created superuser {USERNAME}'))
            return
        user.username = USERNAME
        user.email = EMAIL
        user.set_password(PASSWORD)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Updated superuser {USERNAME}'))
