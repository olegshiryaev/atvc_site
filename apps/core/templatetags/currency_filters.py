from django import template

register = template.Library()


@register.filter
def currency(value):
    if value is None or not isinstance(value, (int, float)):
        return "Цена по запросу"
    return f"{int(value)} ₽"
