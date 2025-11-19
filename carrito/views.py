# carrito/views.py
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse , HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .cart import Cart
from tienda.models import ProductoTalla, Color
from tienda.models import ProductoTalla, Producto
from .utils import build_cart_items_from_session

WHATSAPP_PHONE = getattr(settings, 'WHATSAPP_PHONE', '573025934518')


def _json_error(message, status=400):
    return JsonResponse({'success': False, 'message': message}, status=status)


def _safe_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0.00')


def _cart_total_items(cart):
    """
    Intenta obtener la cantidad total de items usando helpers del Cart.
    Si no existen, calcula a mano a partir del iterable del cart o de la session.
    """
    try:
        return int(cart.get_total_quantity())
    except Exception:
        # intentar iterar
        try:
            return sum(int(item.get('cantidad', item.get('quantity', 0))) for item in cart)
        except Exception:
            # fallback: leer session (estructura que usas en fallback de Cart)
            sess_cart = getattr(cart, 'session', None) or {}
            try:
                if isinstance(sess_cart, dict):
                    return sum(int(v.get('cantidad', 0)) for v in sess_cart.values())
            except Exception:
                pass
    return 0


def _cart_total_price(cart):
    """
    Intenta obtener el precio total. Si falla, sumar 'subtotal' de cada item.
    """
    try:
        total = cart.get_total_price()
        return _safe_decimal(total)
    except Exception:
        try:
            total = sum(_safe_decimal(item.get('subtotal', 0)) for item in cart)
            return total
        except Exception:
            # fallback desde session: intentar reconstruir sumando precio * cantidad
            sess = getattr(cart, 'session', None) or {}
            try:
                total = Decimal('0.00')
                for k, v in (sess or {}).items():
                    precio = _safe_decimal(v.get('precio', 0) or v.get('price', 0))
                    cantidad = int(v.get('cantidad', v.get('quantity', 0) or 0))
                    total += precio * cantidad
                return total
            except Exception:
                return Decimal('0.00')

def _session_cart_items_as_list(request):
    """
    Si no puedes usar list(cart) devuelve una lista de items construida desde
    request.session['carrito'] con info mínima (intentar resolver ProductoTalla).
    """
    sess_cart = request.session.get('carrito', {}) or {}
    out = []
    ids = [int(k) for k in sess_cart.keys() if str(k).isdigit()]
    productos_tallas = ProductoTalla.objects.filter(id__in=ids).select_related('producto', 'talla', 'color')
    pt_map = {pt.id: pt for pt in productos_tallas}
    for k, v in sess_cart.items():
        try:
            pt_id = int(k)
        except Exception:
            continue
        pt = pt_map.get(pt_id)
        cantidad = int(v.get('cantidad', v.get('quantity', 0) or 0))
        subtotal = v.get('subtotal') or (v.get('precio', 0) * cantidad if v.get('precio') else 0)
        out.append({
            'producto_talla_id': pt_id,
            'talla': pt,
            'cantidad': cantidad,
            'subtotal': _safe_decimal(subtotal),
        })
    return out


@require_POST
def agregar_al_carrito(request, *args, **kwargs):
    """
    Vista robusta que acepta distintos nombres de parámetro:
      - pt_id
      - producto_talla_id
      - id
      - cualquier nombre que contenga 'pt' o 'producto'
    Actualiza request.session['cart'] y devuelve JSON.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # intentar extraer el id desde kwargs (soporta varios nombres)
    possible_keys = ['pt_id', 'producto_talla_id', 'producto_id', 'id', 'pk']
    pt_id = None
    for k in possible_keys:
        if k in kwargs and kwargs[k]:
            pt_id = kwargs[k]
            break
    # si no vino por kwargs, intentar leer la URL final (por si usas path with int)
    if pt_id is None:
        # a veces se manda como primer arg posicional
        if args:
            pt_id = args[0]
    # como último recurso, intentar obtener desde POST (no recomendado pero útil)
    if pt_id is None:
        pt_id = request.POST.get('producto_talla_id') or request.POST.get('pt_id') or request.POST.get('id')

    if not pt_id:
        return JsonResponse({'success': False, 'message': 'Falta id de variante'}, status=400)

    try:
        pt_id = int(pt_id)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Id de variante inválido'}, status=400)

    # parsear cantidad
    try:
        cantidad = int(request.POST.get('cantidad', 1))
        if cantidad < 1:
            cantidad = 1
    except Exception:
        cantidad = 1

    # cargar carrito desde session
    cart = request.session.get('cart', {})

    key = str(pt_id)
    # intentar leer datos del producto para completar info si hace falta
    try:
        pt = ProductoTalla.objects.select_related('producto','talla','color').get(pk=pt_id)
        precio = getattr(pt, 'precio', 0)
        nombre = pt.producto.nombre if getattr(pt, 'producto', None) else ''
        imagen = pt.producto.imagen1.url if getattr(pt, 'producto', None) and getattr(pt.producto, 'imagen1', None) else ''
        talla_nombre = pt.talla.nombre if getattr(pt, 'talla', None) else ''
        color_nombre = pt.color.nombre if getattr(pt, 'color', None) else ''
    except ProductoTalla.DoesNotExist:
        pt = None
        precio = request.POST.get('precio', 0)
        nombre = request.POST.get('producto_nombre', '')
        imagen = request.POST.get('imagen_url', '')
        talla_nombre = request.POST.get('talla', '')
        color_nombre = request.POST.get('color', '')

    # actualizar la entry en session
    if key in cart:
        cart[key]['cantidad'] = int(cart[key].get('cantidad', 0)) + cantidad
    else:
        cart[key] = {
            'cantidad': cantidad,
            'precio': str(precio),
            'producto_nombre': nombre,
            'imagen_url': imagen,
            'talla': talla_nombre,
            'color': color_nombre,
        }

    request.session['cart'] = cart
    request.session.modified = True

    # reconstruir datos para el partial y contar unidades
    cart_items, total = build_cart_items_from_session(cart)
    mini_html = render_to_string('carrito/mini_carrito.html', {'cart_items': cart_items, 'total': total}, request=request)
    total_count = sum(int(v.get('cantidad', 0)) for v in cart.values())

    return JsonResponse({
        'success': True,
        'cart_count': total_count,
        'mini_cart_html': mini_html,
    })


@require_POST
def actualizar_cantidad(request, producto_talla_id):
    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except (ValueError, TypeError):
        return _json_error('Cantidad inválida', status=400)

    if cantidad < 0:
        return _json_error('Cantidad inválida', status=400)

    producto_talla = get_object_or_404(ProductoTalla, id=producto_talla_id, activa=True)
    if cantidad > producto_talla.cantidad:
        return _json_error('Stock insuficiente', status=409)

    cart = Cart(request)
    try:
        cart.add(producto_talla_id, cantidad, override=True)
    except TypeError:
        # fallback a session
        sess_cart = request.session.get('carrito', {})
        if str(producto_talla_id) in sess_cart:
            sess_cart[str(producto_talla_id)]['cantidad'] = cantidad
        else:
            sess_cart[str(producto_talla_id)] = {'cantidad': cantidad, 'precio': float(producto_talla.producto.precio_venta)}
        request.session['carrito'] = sess_cart
        request.session.modified = True
    except Exception:
        return _json_error('Error al actualizar el carrito', status=500)

    try:
        cart_items = list(cart)
    except Exception:
        cart_items = _session_cart_items_as_list(request)

    total_items = _cart_total_items(cart)
    total_price = _cart_total_price(cart)

    mini_html = ''
    try:
        mini_html = render_to_string('carrito/mini_carrito.html', {
            'cart_items': cart_items,
            'total': total_price,
            'cart_count': total_items
        }, request=request)
    except Exception:
        mini_html = ''

    return JsonResponse({
        'success': True,
        'cart_count': total_items,
        'cart_total': str(total_price),
        'mini_cart_html': mini_html,
    })


@require_POST
def eliminar_del_carrito(request, producto_talla_id):
    cart = Cart(request)
    try:
        cart.remove(producto_talla_id)
    except Exception:
        sess_cart = request.session.get('carrito', {})
        if str(producto_talla_id) in sess_cart:
            sess_cart.pop(str(producto_talla_id))
            request.session['carrito'] = sess_cart
            request.session.modified = True

    try:
        cart_items = list(cart)
    except Exception:
        cart_items = _session_cart_items_as_list(request)

    total_items = _cart_total_items(cart)
    total_price = _cart_total_price(cart)

    mini_html = ''
    try:
        mini_html = render_to_string('carrito/mini_carrito.html', {
            'cart_items': cart_items,
            'total': total_price,
            'cart_count': total_items
        }, request=request)
    except Exception:
        mini_html = ''

    return JsonResponse({
        'success': True,
        'cart_count': total_items,
        'cart_total': str(total_price),
        'mini_cart_html': mini_html,
    })


def ver_carrito(request):
    cart_data = request.session.get('cart', {})
    cart_items, total = build_cart_items_from_session(cart_data)

    return render(request, 'carrito/ver_carrito.html', {
        'cart_items': cart_items,
        'total': total,
    })

@require_POST
def vaciar_carrito(request):
    Cart(request).clear()
    try:
        request.session.modified = True
    except Exception:
        pass
    messages.success(request, "🧹 Carrito vaciado correctamente.")
    return redirect('carrito:ver_carrito')


def enviar_carrito(request):
    cart = Cart(request)
    try:
        items = list(cart)
    except Exception:
        items = _session_cart_items_as_list(request)

    if len(items) == 0:
        messages.warning(request, "El carrito está vacío.")
        return redirect('carrito:ver_carrito')

    lines = ['*Mi pedido*:']
    for item in items:
        producto_talla = item.get('talla') or getattr(item, 'talla', None)
        if not producto_talla:
            pt_id = item.get('producto_talla_id') or item.get('id') or getattr(item, 'id', None)
            if pt_id:
                try:
                    producto_talla = ProductoTalla.objects.select_related('producto', 'talla', 'color').get(id=pt_id)
                except ProductoTalla.DoesNotExist:
                    producto_talla = None
        if not producto_talla:
            continue

        producto = producto_talla.producto
        talla = producto_talla.talla.nombre if producto_talla.talla else "Sin talla"
        color = producto_talla.color.nombre if getattr(producto_talla, 'color', None) else "Sin color"
        genero = producto_talla.get_genero_display() if hasattr(producto_talla, 'get_genero_display') else (producto_talla.genero or "Sin género")
        cantidad = item.get('cantidad', item.get('quantity', 0))
        subtotal = item.get('subtotal') or (getattr(item, 'subtotal', None) or 0)

        lines.append(f"- {producto.nombre} (T: {talla}, C: {color}, G: {genero}) x{cantidad} = ${subtotal}")

    total = _cart_total_price(cart)
    lines.append(f"*Total: ${total}*")

    text = quote("\n".join(lines))
    url = f"https://wa.me/{WHATSAPP_PHONE}?text={text}"
    return HttpResponseRedirect(url)

def mini_cart_partial(request):
    cart = Cart(request)
    html = render_to_string('carrito/mini_carrito.html', {
        'cart_items': list(cart),
        'total': cart.get_total_price(),
        'cart_count': sum(item.get('cantidad', item.get('quantity',0)) for item in cart)
    }, request=request)
    return HttpResponse(html)