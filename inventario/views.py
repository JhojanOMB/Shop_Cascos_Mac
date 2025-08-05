from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from tienda.models import *
from inventario.models import *
from .forms import *
from django.db.models import Q, Sum, F, FloatField

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

    variantes = (
        ProductoTalla.objects
        .select_related('producto', 'talla', 'color')
        .all()
    )
    if query:
        variantes = variantes.filter(
            Q(producto__nombre__icontains=query) |
            Q(producto__referencia__icontains=query) |
            Q(codigo_barras__icontains=query)
        )

    variantes_sin_stock  = variantes.filter(cantidad=0)
    variantes_bajo_stock = variantes.filter(cantidad__gt=0, cantidad__lte=5)
    variantes_con_stock  = variantes.filter(cantidad__gt=5)

    page_sin  = Paginator(variantes_sin_stock, 10).get_page(request.GET.get('page_sin'))
    page_bajo = Paginator(variantes_bajo_stock, 10).get_page(request.GET.get('page_bajo'))
    page_con  = Paginator(variantes_con_stock, 10).get_page(request.GET.get('page_con'))

    # sumando solo variantes con stock
    totales = variantes_con_stock.aggregate(
        total_compra=Sum(F('cantidad') * F('producto__precio_compra'), output_field=FloatField()),
        total_venta=Sum(F('cantidad') * F('producto__precio_venta'), output_field=FloatField()),
        total_unidades=Sum('cantidad')
    )

    context = {
        'variantes_sin_stock': page_sin,
        'variantes_bajo_stock': page_bajo,
        'variantes_con_stock': page_con,
        'search_query': query,
        'categorias': Categoria.objects.all(),
        'proveedores': Proveedor.objects.all(),
        # Totales para las tarjetas
        'total_compra': totales['total_compra'] or 0,
        'total_venta': totales['total_venta'] or 0,
        'total_unidades': totales['total_unidades'] or 0,
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