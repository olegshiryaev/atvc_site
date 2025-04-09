# Generated by Django 5.1.7 on 2025-03-30 20:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Office',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Офис обслуживания', max_length=100)),
                ('image', models.ImageField(upload_to='office_images/')),
                ('city', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=20)),
                ('longitude', models.FloatField()),
                ('latitude', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='WorkSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('days', models.CharField(max_length=50)),
                ('hours', models.CharField(max_length=50)),
                ('office', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='core.office')),
            ],
        ),
    ]
