from django.core.management.base import BaseCommand

from api.models import User


class Command(BaseCommand):
    help = 'Ensure default admin, accountant, and agent users exist with preset passwords and roles.'

    DEFAULT_USERS = [
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'name': 'System Admin',
            'role': 'admin',
            'is_superuser': True,
            'is_staff': True,
            'password': 'admin123',
        },
        {
            'username': 'accountant',
            'email': 'accountant@dipcom.com',
            'name': 'Head Accountant',
            'role': 'accountant',
            'is_superuser': False,
            'is_staff': False,
            'password': 'accountant123',
        },
        {
            'username': 'agent',
            'email': 'agent@example.com',
            'name': 'Terminal Agent',
            'role': 'agent',
            'is_superuser': False,
            'is_staff': False,
            'password': 'agent123',
        },
    ]

    def handle(self, *args, **options):
        for user_data in self.DEFAULT_USERS:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'name': user_data['name'],
                    'role': user_data['role'],
                    'is_superuser': user_data['is_superuser'],
                    'is_staff': user_data['is_staff'],
                },
            )

            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {user.username}"))
                continue

            changed = False
            for field in ('email', 'name', 'role', 'is_superuser', 'is_staff'):
                if getattr(user, field) != user_data[field]:
                    setattr(user, field, user_data[field])
                    changed = True

            # Keep the command idempotent by ensuring the default password is always set.
            user.set_password(user_data['password'])
            changed = True

            if changed:
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Updated user: {user.username}"))
            else:
                self.stdout.write(f"No changes for user: {user.username}")

        self.stdout.write(self.style.SUCCESS('Default users initialization complete.'))
