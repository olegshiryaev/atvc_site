from django import template

register = template.Library()


@register.simple_tag
def file_icon(extension):
    icons = {
        "PDF": "bi-file-earmark-pdf",
        "DOC": "bi-file-earmark-word",
        "DOCX": "bi-file-earmark-word",
        "XLS": "bi-file-earmark-excel",
        "XLSX": "bi-file-earmark-excel",
        "PPT": "bi-file-earmark-ppt",
        "PPTX": "bi-file-earmark-ppt",
        "JPG": "bi-file-earmark-image",
        "JPEG": "bi-file-earmark-image",
        "PNG": "bi-file-earmark-image",
    }
    return icons.get(extension.upper(), "bi-file-earmark")


@register.simple_tag
def file_color(extension):
    colors = {
        "PDF": "text-danger",  # Красный
        "DOC": "text-primary",  # Синий
        "DOCX": "text-primary",
        "XLS": "text-success",  # Зелёный
        "XLSX": "text-success",
        "PPT": "text-warning",  # Оранжевый
        "PPTX": "text-warning",
        "JPG": "text-info",  # Бирюзовый
        "JPEG": "text-info",
        "PNG": "text-info",
    }
    return colors.get(extension.upper(), "text-secondary")
