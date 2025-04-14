# Generated by Django 5.1.7 on 2025-04-11 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_company'),
    ]

    operations = [
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Заголовок')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('image', models.ImageField(upload_to='banners/', verbose_name='Изображение')),
                ('button_text', models.CharField(default='Подробнее', max_length=100, verbose_name='Текст кнопки')),
                ('link', models.URLField(blank=True, verbose_name='Ссылка')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок показа')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
            ],
            options={
                'verbose_name': 'Баннер',
                'verbose_name_plural': 'Баннеры',
                'ordering': ['order'],
            },
        ),
    ]
