from django import template

register = template.Library()


@register.filter(name="decline_channel")
def decline_channel(value):
    try:
        count = int(value)
    except (ValueError, TypeError):
        return "каналов"

    rest100 = count % 100
    if 11 <= rest100 <= 14:
        return "каналов"

    rest10 = count % 10
    if rest10 == 1:
        return "канал"
    elif 2 <= rest10 <= 4:
        return "канала"
    else:
        return "каналов"
