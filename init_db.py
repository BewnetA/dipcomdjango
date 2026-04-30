import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import User, MarketingAgent

def init():
    # Create Superuser
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123', name='System Admin', role='admin')
        print("Superuser created: admin / admin123")
    
    # Create an Agent
    if not User.objects.filter(username='agent').exists():
        User.objects.create_user('agent', 'agent@example.com', 'agent123', name='Terminal Agent', role='agent')
        print("Agent created: agent / agent123")

    # Accountant (JWT login uses username; demo UI accepts this email as identifier)
    if not User.objects.filter(username='accountant').exists():
        User.objects.create_user(
            'accountant', 'accountant@dipcom.com', 'accountant123',
            name='Head Accountant', role='accountant',
        )
        print("Accountant created: accountant / accountant123")
    
    # Create Default Marketing Agent
    if not MarketingAgent.objects.filter(name='Direct Reach').exists():
        MarketingAgent.objects.create(name='Direct Reach', commission_rate=0)
        print("Default Marketing Agent created.")

if __name__ == '__main__':
    init()
