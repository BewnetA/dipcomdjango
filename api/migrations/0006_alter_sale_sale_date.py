# Generated manually for historical sale backdating support

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_remove_user_email_verified_remove_user_otp_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='sale_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
