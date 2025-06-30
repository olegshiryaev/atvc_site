from django import template

register = template.Library()

@register.filter
def color_to_hex(color):
    color_map = {
            'white': '#ffffff',
            'black': '#000000',
            'gray': '#808080',
            'other': '#d3d3d3',
    }
    return color_map.get(color, '#d3d3d3')