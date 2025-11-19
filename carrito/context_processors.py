# carrito/context_processors.py
from .utils import build_mini_cart_from_session

def cart_context(request):
    cart_data = request.session.get('cart', {})
    mini_items, total_items, mini_total = build_mini_cart_from_session(cart_data)
    return {
        'mini_cart_items': mini_items,           # lista de items para mini-carrito
        'total_items_carrito': total_items,      # número total de unidades en el badge
        'mini_cart_total': mini_total,           # total en dinero del mini-carrito
    }


def carrito_total_items(request):
    """
    Ejemplo adicional: sólo número total de items.
    """
    cart_data = request.session.get('cart', {})
    total_items = 0
    if isinstance(cart_data, dict):
        for v in cart_data.values():
            try:
                total_items += int(v.get('cantidad', v.get('qty', 1)))
            except Exception:
                total_items += 0
    return {'cart_total_items': total_items}
