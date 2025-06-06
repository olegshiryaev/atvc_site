# Generated by Django 5.1.7 on 2025-04-09 22:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_device'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(unique=True, verbose_name='Код')),
                ('name', models.CharField(max_length=100, verbose_name='Название услуги')),
            ],
            options={
                'verbose_name': 'Тип услуги',
                'verbose_name_plural': 'Типы услуг',
            },
        ),
        migrations.RemoveField(
            model_name='device',
            name='service_type',
        ),
        migrations.AddField(
            model_name='device',
            name='service_types',
            field=models.ManyToManyField(related_name='devices', to='core.service', verbose_name='Типы услуги'),
        ),
    ]
