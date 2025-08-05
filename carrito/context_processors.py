def carrito_total_items(request):
    carrito = request.session.get('carrito', {})
    total_items = sum(item['cantidad'] for item in carrito.values())
    return {'total_items_carrito': total_items}
