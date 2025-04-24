from django import template
from ..models import Locality

register = template.Library()


@register.simple_tag
def get_localities(current_locality):
    localities = Locality.objects.filter(is_active=True).order_by("name")
    return localities
