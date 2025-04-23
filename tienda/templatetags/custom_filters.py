# tienda/templatetags/custom_filters.py

import base64
from django import template
from io import BytesIO
from PIL import Image

register = template.Library()

@register.filter(name='add_class')
def add_class(field, args):
    """Añade clase y placeholders a los campos del formulario."""
    try:
        # Separar los argumentos (clases y atributos)
        parts = args.split(',')
        css_class = parts[0].strip()  # Primer parámetro es la clase CSS
        placeholder = parts[1].strip() if len(parts) > 1 else None  # Segundo parámetro es el placeholder (opcional)

        # Preparar los atributos
        attrs = {'class': css_class}
        if placeholder:
            attrs['placeholder'] = placeholder

        # Devolver el campo con los atributos añadidos
        return field.as_widget(attrs=attrs)
    except AttributeError:
        # Si field es una cadena u otro objeto sin as_widget, devolver el field tal cual
        return field

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0) 

@register.filter
def base64_image(image):
    """Convierte una imagen en base64."""
    if image:
        image_data = BytesIO()
        img = Image.open(image)
        img.save(image_data, format='PNG')
        return base64.b64encode(image_data.getvalue()).decode('utf-8')
    return ''
