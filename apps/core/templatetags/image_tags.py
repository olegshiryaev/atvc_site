from django import template
from imagekit.templatetags.imagekit import thumbnail

register = template.Library()

@register.filter
def resize_image(image, size):
    return thumbnail(image, size, crop='center', quality=85)