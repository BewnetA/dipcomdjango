from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        """
        Dev convenience: ensure demo users exist so JWT login works
        without manually running init_db.py after every fresh DB.
        """
        try:
            from django.conf import settings
            if not getattr(settings, 'DEBUG', False):
                return

            from django.db.utils import OperationalError, ProgrammingError
            from .models import User, MarketingAgent

            # DB might not be migrated yet.
            try:
                User.objects.exists()
            except (OperationalError, ProgrammingError):
                return

            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser(
                    'admin', 'admin@example.com', 'admin123',
                    name='System Admin', role='admin',
                )
            if not User.objects.filter(username='agent').exists():
                User.objects.create_user(
                    'agent', 'agent@example.com', 'agent123',
                    name='Terminal Agent', role='agent',
                )
            if not User.objects.filter(username='accountant').exists():
                User.objects.create_user(
                    'accountant', 'accountant@dipcom.com', 'accountant123',
                    name='Head Accountant', role='accountant',
                )

            if not MarketingAgent.objects.filter(name='Direct Reach').exists():
                MarketingAgent.objects.create(name='Direct Reach', commission_rate=0)
        except Exception:
            # Avoid preventing app startup in dev.
            return
