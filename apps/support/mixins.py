from django.urls import reverse

class BreadcrumbMixin:
    """
    Миксин для добавления хлебных крошек в контекст.
    Совместим с шаблоном, использующим:
        {% url crumb.url locality_slug=locality.slug %}
    """

    def get_breadcrumbs(self):
        """
        Переопределите этот метод в представлении.
        Должен возвращать список словарей:
        [
            {'url': 'имя_вьюшки', 'title': '...', 'доп_параметры...'},
            {'url': None, 'title': 'Текущая страница'}
        ]
        """
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        breadcrumbs = self.get_breadcrumbs()

        # Добавляем locality_slug в каждый элемент, если он есть
        locality = getattr(self, 'locality', None)
        if locality and breadcrumbs:
            for crumb in breadcrumbs:
                # Не добавляем locality_slug, если это уже URL (на всякий случай)
                if crumb.get('url') and 'locality_slug' not in crumb:
                    crumb['locality_slug'] = locality.slug

        context['breadcrumbs'] = breadcrumbs
        return context