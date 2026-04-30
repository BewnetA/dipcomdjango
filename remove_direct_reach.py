import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import MarketingAgent

ma = MarketingAgent.objects.filter(name='Direct Reach').first()
if ma:
    ma.delete()
    print('Direct Reach deleted from MarketingAgent')
else:
    print('Direct Reach not found in MarketingAgent')
