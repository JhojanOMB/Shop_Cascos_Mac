from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from tienda.models import ProductoTalla

def agregar_al_carrito(request, producto_talla_id):
    if request.method == 'POST':
        producto_talla = get_object_or_404(ProductoTalla, id=producto_talla_id)
        carrito = request.session.get('carrito', {})

        if str(producto_talla_id) in carrito:
            carrito[str(producto_talla_id)]['cantidad'] += int(request.POST.get('cantidad', 1))
        else:
            carrito[str(producto_talla_id)] = {
                'producto': producto_talla.producto.nombre,
                'talla': producto_talla.talla.nombre,
                'cantidad': int(request.POST.get('cantidad', 1))
            }

        request.session['carrito'] = carrito

        # Devolver una respuesta JSON
        return JsonResponse({'success': True, 'message': 'Producto añadido al carrito'})
    else:
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)



def ver_carrito(request):
    carrito = request.session.get('carrito', {})
    return render(request, 'carrito/ver_carrito.html', {'carrito': carrito})

def eliminar_del_carrito(request, producto_talla_id):
    carrito = request.session.get('carrito', {})
    if str(producto_talla_id) in carrito:
        del carrito[str(producto_talla_id)]
    request.session['carrito'] = carrito
    return redirect('carrito:ver_carrito')

def actualizar_cantidad(request, producto_talla_id):
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))
        carrito = request.session.get('carrito', {})

        if str(producto_talla_id) in carrito:
            carrito[str(producto_talla_id)]['cantidad'] = cantidad

        request.session['carrito'] = carrito
    return redirect('carrito:ver_carrito')

def enviar_carrito(request):
    carrito = request.session.get('carrito', {})
    lista_productos = "\n".join([f"{item['cantidad']} x {item['producto']} ({item['talla']})" for item in carrito.values()])
    mensaje = f"Lista de productos:\n{lista_productos}"
    url = f"https://wa.me/573212692311?text={mensaje}"
    return redirect(url)
