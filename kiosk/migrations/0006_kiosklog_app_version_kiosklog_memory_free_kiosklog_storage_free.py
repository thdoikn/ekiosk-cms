from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kiosk', '0005_ekiosk_offline_notified_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='kiosklog',
            name='app_version',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='kiosklog',
            name='storage_free',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kiosklog',
            name='memory_free',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]
