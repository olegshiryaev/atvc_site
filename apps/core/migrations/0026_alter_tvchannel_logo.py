# Generated by Django 5.1.7 on 2025-04-17 13:17

import apps.core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_tvchannel_alter_tariff_options_alter_tariff_channels_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tvchannel',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to=apps.core.models.channel_logo_upload_to, verbose_name='Логотип канала'),
        ),
    ]
