# tienda/templatetags/custom_filters.py

import base64
from django import template
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='add_class')
def add_class(field, args):
    """
    Añade clase y atributos a los campos del formulario.
    Uso:
      {{ form.field|add_class:"mi-clase" }}
      {{ form.field|add_class:"mi-clase;placeholder=Buscar..." }}
      {{ form.field|add_class:"mi-clase;placeholder=Texto;aria-label=buscar" }}

    Nota: los atributos adicionales se separan con ';' y cada atributo con '='
    """
    try:
        # separar por ';' para evitar problemas si el placeholder contiene comas
        parts = [p.strip() for p in args.split(';') if p.strip()]
        css_class = parts[0] if parts else ''
        attrs = {}
        if css_class:
            attrs['class'] = css_class

        # parsear atributos adicionales key=value
        for extra in parts[1:]:
            if '=' in extra:
                k, v = extra.split('=', 1)
                attrs[k.strip()] = v.strip()
        # devolver el widget con los atributos añadidos
        return field.as_widget(attrs=attrs)
    except Exception:
        # Si field no tiene as_widget (p. ej. es str), devolver tal cual
        try:
            return field
        except Exception:
            return ''


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Devuelve dictionary.get(key, []) de forma segura.
    - Si 'dictionary' es None devuelve [].
    - Si la key es numérica y el dict usa enteros como keys, se intenta convertir.
    - Si dictionary es una lista y la key es índice, intenta devolver el elemento.
    Uso en template:
      {% load custom_filters %}
      {{ colores_por_producto|get_item:producto.id }}
    """
    if not dictionary:
        return []

    # intentar convertir key numérico
    try:
        # string que contiene dígitos => int
        if isinstance(key, str) and key.isdigit():
            ik = int(key)
        else:
            ik = key
    except Exception:
        ik = key

    # si es dict
    try:
        if isinstance(dictionary, dict):
            return dictionary.get(ik) or dictionary.get(str(ik)) or []
        # si es lista/iterable y key es índice
        if isinstance(dictionary, (list, tuple)):
            try:
                idx = int(ik)
                return dictionary[idx] if 0 <= idx < len(dictionary) else []
            except Exception:
                return []
        # fallback: intentar getattr
        return getattr(dictionary, ik, []) or []
    except Exception:
        return []


@register.filter(name='base64_image')
def base64_image(image):
    """
    Convierte una imagen (FileField/ImageField o camino a archivo) en base64 (PNG).
    Devuelve cadena vacía si falla.
    Uso en template:
      <img src="data:image/png;base64,{{ producto.imagen|base64_image }}" />
    """
    if not image:
        return ''

    try:
        image_data = BytesIO()
        # si image es un FieldFile, obtener su file/read()
        try:
            # algunos FieldFile tienen .file o .open(); PIL acepta file-like
            img = Image.open(image)
        except (UnidentifiedImageError, TypeError, AttributeError):
            # intentar abrir desde .file o .path
            try:
                img = Image.open(image.file)
            except Exception:
                try:
                    img = Image.open(image.path)
                except Exception:
                    return ''
        # normalizar (convertir a RGBA o RGB según sea necesario)
        try:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
        except Exception:
            pass

        img.save(image_data, format='PNG')
        image_data.seek(0)
        encoded = base64.b64encode(image_data.getvalue()).decode('utf-8')
        return mark_safe(encoded)
    except Exception:
        return ''
