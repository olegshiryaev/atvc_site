# Generated by Django 5.1.7 on 2025-04-17 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_tvchannel_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tvchannel',
            name='category',
            field=models.CharField(blank=True, choices=[('broadcast', 'Эфирные'), ('education', 'Познавательные'), ('entertainment', 'Развлекательные'), ('kids', 'Детям'), ('movie', 'Кино'), ('music', 'Музыка'), ('news', 'Бизнес, новости'), ('sport', 'Спорт')], max_length=20, verbose_name='Категория'),
        ),
    ]
