# carrito/utils.py
from decimal import Decimal
from tienda.models import ProductoTalla

def build_cart_items_from_session(cart_data):
    """
    Convierte el diccionario de sesión en una lista de items normalizados
    para la vista completa del carrito.
    """
    items = []
    total = Decimal('0.00')

    for key, val in cart_data.items():
        cantidad = int(val.get('cantidad', 0))
        precio = Decimal(val.get('precio', '0'))  # si guardas 0 en sesión, ajustar luego
        subtotal = precio * cantidad

        # si el precio en sesión es 0, intentar sacar de ProductoTalla
        if precio == 0:
            try:
                from tienda.models import ProductoTalla
                pt = ProductoTalla.objects.select_related('producto').get(id=key)
                precio = Decimal(getattr(pt.producto, 'precio_venta', 0))
                subtotal = precio * cantidad
            except Exception:
                precio = Decimal('0')
                subtotal = Decimal('0')

        items.append({
            'producto_nombre': val.get('producto_nombre', ''),
            'imagen_url': val.get('imagen_url', ''),
            'producto_talla_id': key,
            'talla_nombre': val.get('talla', ''),
            'color_nombre': val.get('color', ''),
            'genero_display': val.get('genero', ''),
            'cantidad': cantidad,
            'precio': precio,
            'subtotal': subtotal,
        })
        total += subtotal

    return items, total


def build_mini_cart_from_session(cart_data):
    """
    Estructura minimal para el mini-carrito (badge/header).
    Devuelve (mini_items_list, total_count, total_decimal).
    Cada mini item: {'producto_talla_id', 'producto_nombre', 'imagen_url', 'cantidad', 'subtotal'}
    """
    mini = []
    total = Decimal('0.00')
    count = 0
    if not isinstance(cart_data, dict):
        return mini, count, total

    for key, data in cart_data.items():
        try:
            pt_id = int(key)
        except Exception:
            pt_id = key

        cantidad = int(data.get('cantidad', data.get('qty', 1)))
        precio = data.get('precio', 0)
        try:
            precio_dec = Decimal(str(precio))
        except Exception:
            precio_dec = Decimal('0.00')

        subtotal = precio_dec * cantidad
        total += subtotal
        count += cantidad

        mini.append({
            'producto_talla_id': pt_id,
            'producto_nombre': data.get('producto_nombre', '')[:40],  # acortar por si acaso
            'imagen_url': data.get('imagen_url', ''),
            'cantidad': cantidad,
            'subtotal': subtotal,
        })

    return mini, count, total
