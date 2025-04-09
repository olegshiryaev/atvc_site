# Generated by Django 5.1.7 on 2025-04-08 16:09

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_tariff_technology_application'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=255, verbose_name='Тема письма')),
                ('email', models.EmailField(max_length=255, verbose_name='Электронный адрес (email)')),
                ('content', models.TextField(verbose_name='Содержимое письма')),
                ('time_create', models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP отправителя')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Обратная связь',
                'verbose_name_plural': 'Обратная связь',
                'db_table': 'app_feedback',
                'ordering': ['-time_create'],
            },
        ),
    ]
