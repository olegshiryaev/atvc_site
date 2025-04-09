from django import template
from ..models import City

register = template.Library()


@register.simple_tag
def get_cities(current_city):
    return City.objects.filter(is_active=True).exclude(id=current_city.id)
