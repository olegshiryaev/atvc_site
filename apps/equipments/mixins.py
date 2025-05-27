from .models import ViewCount
from apps.services.utils import get_client_ip


class ViewCountMixin:
    def get_object(self):
        obj = super().get_object()
        ip_address = get_client_ip(self.request)
        session_key = self.request.session.session_key
        user = self.request.user if self.request.user.is_authenticated else None

        # Записываем каждый просмотр как отдельную запись
        ViewCount.objects.create(
            product=obj, ip_address=ip_address, session_key=session_key, user=user
        )

        return obj
