from decimal import Decimal
from django.conf import settings
from tienda.models import ProductoTalla

SESSION_KEY = 'carrito'

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(SESSION_KEY)
        if not cart:
            cart = self.session[SESSION_KEY] = {}
        self.cart = cart

    def add(self, talla_id, cantidad=1, override=False):
        """
        Añade o actualiza la cantidad de un ítem en el carrito.
        Si override=True reemplaza la cantidad, sino suma.
        """
        key = str(talla_id)
        if key in self.cart:
            if override:
                self.cart[key]['cantidad'] = cantidad
            else:
                self.cart[key]['cantidad'] += cantidad
        else:
            self.cart[key] = {'cantidad': cantidad}
        self.session.modified = True

    def remove(self, talla_id):
        """Elimina un ítem del carrito."""
        key = str(talla_id)
        if key in self.cart:
            del self.cart[key]
            self.session.modified = True

    def clear(self):
        """Vacía todo el carrito de la sesión."""
        self.session.pop(SESSION_KEY, None)
        self.session.modified = True

    def __iter__(self):
        """
        Itera los ítems devolviendo un dict con:
        talla, cantidad, precio y subtotal.
        """
        ids = self.cart.keys()
        tallas = ProductoTalla.objects.filter(id__in=ids).select_related('producto', 'talla')
        for talla in tallas:
            cantidad = self.cart[str(talla.id)]['cantidad']
            precio = talla.producto.precio_venta
            yield {
                'talla': talla,
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': Decimal(precio) * cantidad,
            }

    def __len__(self):
        """Total de unidades en el carrito."""
        return sum(item['cantidad'] for item in self.cart.values())

    def get_total_price(self):
        """Importe total del carrito."""
        return sum(item['cantidad'] * item['precio'] for item in self)