from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from urllib.parse import quote
from .cart import Cart
from tienda.models import ProductoTalla
from django.contrib import messages

# Número de WhatsApp en formato internacional sin '+'
WHATSAPP_PHONE = '573212692311'

@require_POST
def agregar_al_carrito(request, producto_talla_id):
    """Añade un producto al carrito vía AJAX."""
    producto_talla = get_object_or_404(ProductoTalla, id=producto_talla_id)
    cart = Cart(request)
    cantidad = int(request.POST.get('cantidad', 1))
    cart.add(producto_talla_id, cantidad)
    return JsonResponse({'success': True, 'cart_count': len(cart)})

@require_POST
def actualizar_cantidad(request, producto_talla_id):
    """Reemplaza la cantidad de un ítem."""
    cantidad = int(request.POST.get('cantidad', 1))
    cart = Cart(request)
    cart.add(producto_talla_id, cantidad, override=True)
    return JsonResponse({'success': True, 'cart_count': len(cart)})

@require_POST
def eliminar_del_carrito(request, producto_talla_id):
    """Elimina un ítem del carrito."""
    cart = Cart(request)
    cart.remove(producto_talla_id)
    return JsonResponse({'success': True, 'cart_count': len(cart)})

def ver_carrito(request):
    """Renderiza la vista del carrito con items y total."""
    cart = Cart(request)
    return render(request, 'carrito/ver_carrito.html', {
        'cart_items': list(cart),
        'total': cart.get_total_price(),
    })

@require_POST
def vaciar_carrito(request):
    """Vacía todo el carrito y redirige con mensaje de éxito."""
    Cart(request).clear()
    messages.success(request, "🧹 Carrito vaciado correctamente.")
    return redirect('carrito:ver_carrito')

def enviar_carrito(request):
    """Genera enlace de WhatsApp con el pedido y redirige."""
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('carrito:ver_carrito')

    lines = ['*Mi pedido*:']
    for item in cart:
        producto_talla = item['talla']
        producto = producto_talla.producto
        talla = producto_talla.talla.nombre
        color = producto_talla.color.nombre if producto_talla.color else "Sin color"
        genero = producto_talla.genero if producto_talla.genero else "Sin género"
        cantidad = item['cantidad']
        subtotal = item['subtotal']

        lines.append(f"- {producto.nombre} (Talla: {talla}, Color: {color}, Género: {genero}) x{cantidad} = ${subtotal}")
    lines.append(f"*Total: ${cart.get_total_price()}*")

    text = quote("\n".join(lines))
    url = f"https://wa.me/{WHATSAPP_PHONE}?text={text}"
    return HttpResponseRedirect(url)