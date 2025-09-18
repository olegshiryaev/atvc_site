from datetime import datetime
from zoneinfo import ZoneInfo


def get_client_ip(request):
    """
    Получение IP адреса
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def is_business_hours(timezone_str='Europe/Moscow'):
    """
    Проверяет, является ли текущее время рабочим.
    Рабочее время: Ежедневно, 8:00 - 21:00 по указанному часовому поясу.
    """
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    # Проверяем время (часы)
    return 8 <= now.hour < 21