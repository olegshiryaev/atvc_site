# Generated by Django 5.1.7 on 2025-04-14 00:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_application_city'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='application',
            name='tariff',
        ),
    ]
