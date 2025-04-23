from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from tienda.models import *
from inventario.models import *
from .forms import *

# Función auxiliar para obtener cantidades por talla y el total del producto
def obtener_cantidades_por_talla_y_total(producto_id):
    producto = Producto.objects.get(id=producto_id)
    tallas_detalle = ProductoTalla.objects.filter(producto=producto)
    
    cantidades_por_talla = {}
    cantidad_total = 0

    for detalle in tallas_detalle:
        cantidades_por_talla[detalle.talla.nombre] = detalle.cantidad
        cantidad_total += detalle.cantidad  # Sumar las cantidades por talla

    return cantidades_por_talla, cantidad_total

# Función auxiliar para obtener la cantidad total en el inventario para un producto
def obtener_cantidades_inventario(producto_id):
    inventarios = Inventario.objects.filter(producto_id=producto_id)
    cantidad_total_inventario = 0
    for inventario in inventarios:
        cantidad_total_inventario += inventario.cantidad
    return cantidad_total_inventario

@login_required
def inventario_view(request):
    query = request.GET.get('search', '')
    
    productos = Producto.objects.all().order_by('nombre')
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(referencia__icontains=query) |
            Q(codigo_barras__icontains=query)
        )

    # Convertir la QuerySet en lista para clasificar según stock
    productos = list(productos)
    productos_con_stock = []
    productos_sin_stock = []
    productos_bajo_stock = []
    
    for producto in productos:
        total_cantidad = producto.total_cantidad  # La propiedad que debe considerar variantes o el campo cantidad
        if total_cantidad == 0:
            productos_sin_stock.append(producto)
        elif total_cantidad <= 5:
            productos_bajo_stock.append(producto)
        else:
            productos_con_stock.append(producto)
            
    # Opcional: asignar variantes a cada producto (si es necesario para mostrar en la tabla)
    for producto in productos:
        producto.variantes = ProductoTalla.objects.filter(
            producto=producto,
            cantidad__gt=0
        ).select_related('talla', 'color')

    # Paginación para cada lista (10 productos por página)
    paginator_con = Paginator(productos_con_stock, 10)
    paginator_sin = Paginator(productos_sin_stock, 10)
    page_con = request.GET.get('page_con')
    page_sin = request.GET.get('page_sin')
    page_obj_con = paginator_con.get_page(page_con)
    page_obj_sin = paginator_sin.get_page(page_sin)
    
    context = {
        'productos_con_stock': page_obj_con,  # Este es el objeto Page para productos con stock
        'productos_sin_stock': page_obj_sin,    # Objeto Page para productos sin stock
        'productos_bajo_stock': productos_bajo_stock,  # Si querés mostrarlos sin paginación o aplicá la misma lógica
        'search_query': query,
        'categorias': Categoria.objects.all(),
        'proveedores': Proveedor.objects.all(),
    }
    return render(request, 'dashboard/inventario/inventario.html', context)

@login_required
def actualizar_cantidad_view(request, pk):
    # Se obtiene la variante del producto
    producto_talla = get_object_or_404(ProductoTalla, pk=pk)
    if request.method == 'POST':
        form = ActualizarCantidadForm(request.POST, instance=producto_talla)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cantidad actualizada correctamente.')
            return redirect('inventario')  # Verificá que esta URL esté definida
    else:
        form = ActualizarCantidadForm(instance=producto_talla)
    return render(request, 'dashboard/inventario/actualizar_cantidad.html', {'form': form})

@login_required
def movimiento_inventario_view(request):
    # Capturamos el producto_talla_id enviado en la URL
    producto_talla_id = request.GET.get('producto_talla_id')
    
    if request.method == 'POST':
        form = MovimientoInventarioForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario = request.user
            movimiento.save()
            messages.success(request, 'Movimiento registrado exitosamente.')
            return redirect('inventario')
    else:
        initial = {}
        if producto_talla_id:
            initial['producto_talla'] = producto_talla_id
            form = MovimientoInventarioForm(initial=initial, producto_talla_id=producto_talla_id)
        else:
            form = MovimientoInventarioForm()
            
    return render(request, 'dashboard/inventario/movimiento_inventario.html', {'form': form})