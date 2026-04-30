import os
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Backs up the SQLite database to prevents data loss'

    def handle(self, *args, **options):
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
        
        try:
            shutil.copy2(db_path, backup_path)
            self.stdout.write(self.style.SUCCESS(f'Successfully backed up database to {backup_path}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Backup failed: {str(e)}'))
