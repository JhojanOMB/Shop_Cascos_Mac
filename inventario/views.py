from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tienda.models import Producto, ProductoTalla
from inventario.models import Inventario
from django.db.models import Q

# Obtener las cantidades por talla y el total del producto
def obtener_cantidades_por_talla_y_total(producto_id):
    producto = Producto.objects.get(id=producto_id)
    tallas_detalle = ProductoTalla.objects.filter(producto=producto)
    
    cantidades_por_talla = {}
    cantidad_total = 0

    for detalle in tallas_detalle:
        cantidades_por_talla[detalle.talla.nombre] = detalle.cantidad
        cantidad_total += detalle.cantidad  # Sumar las cantidades por talla

    return cantidades_por_talla, cantidad_total

# Obtener la cantidad total en el inventario del producto
def obtener_cantidades_inventario(producto_id):
    inventarios = Inventario.objects.filter(producto_id=producto_id)
    cantidad_total_inventario = 0
    for inventario in inventarios:
        cantidad_total_inventario += inventario.cantidad

    return cantidad_total_inventario

@login_required
def inventario_view(request):
    # Obtener todos los productos
    productos = Producto.objects.all()

    # Obtener el valor de búsqueda enviado por el usuario
    query = request.GET.get('search', '')

    # Filtrar productos si hay una búsqueda
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(referencia__icontains=query) |
            Q(codigo_barras__icontains=query)
        )

    # Inicializar listas para los productos filtrados
    productos_con_stock = []
    productos_sin_stock = []
    productos_bajo_stock = []

    # Filtrar productos y calcular la cantidad total
    for producto in productos:
        # Calcula la cantidad total usando la propiedad `total_cantidad`
        total_cantidad = producto.total_cantidad  # No necesitas asignarlo

        # Filtrar según la cantidad
        if total_cantidad > 0:
            productos_con_stock.append(producto)
        elif total_cantidad == 0:
            productos_sin_stock.append(producto)
        elif total_cantidad <= 5:
            productos_bajo_stock.append(producto)

    # Pasa los productos con las categorías correspondientes
    context = {
        'productos_con_stock': productos_con_stock,
        'productos_sin_stock': productos_sin_stock,
        'productos_bajo_stock': productos_bajo_stock,
        'search_query': query,  # Pasar la búsqueda actual al template
    }

    return render(request, 'dashboard/inventario/inventario.html', context)