# Generated by Django 5.1.7 on 2025-04-01 21:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_tariff_cities_tariff_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='tariff',
            name='technology',
            field=models.CharField(blank=True, choices=[('fttx', 'FTTx (Fiber to the x)'), ('pon', 'PON')], default='fttx', max_length=20, verbose_name='Технология подключения'),
        ),
    ]
