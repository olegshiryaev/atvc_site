# Generated by Django 5.1.7 on 2025-05-02 17:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0042_device_device_type_alter_device_image_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='price',
            field=models.IntegerField(verbose_name='Цена'),
        ),
    ]
