from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kiosk', '0004_ekiosk_latitude_ekiosk_longitude_ekiosk_stop_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='ekiosk',
            name='offline_notified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
