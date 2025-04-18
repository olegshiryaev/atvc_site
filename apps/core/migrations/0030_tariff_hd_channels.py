# Generated by Django 5.1.7 on 2025-04-18 13:25

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_alter_tvchannel_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='tariff',
            name='hd_channels',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Количество HD каналов'),
        ),
    ]
