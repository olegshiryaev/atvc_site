# Generated by Django 5.1.7 on 2025-04-09 22:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_feedback'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tariff',
            old_name='tariff_type',
            new_name='service_type',
        ),
    ]
