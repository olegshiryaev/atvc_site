# Generated by Django 5.1.7 on 2025-04-01 11:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cities', '0001_initial'),
        ('core', '0003_tariff'),
    ]

    operations = [
        migrations.AddField(
            model_name='tariff',
            name='cities',
            field=models.ManyToManyField(related_name='tariffs', to='cities.locality', verbose_name='Города'),
        ),
        migrations.AddField(
            model_name='tariff',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активен'),
        ),
    ]
