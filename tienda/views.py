from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.views.generic import ListView, UpdateView, DeleteView, CreateView, DetailView, TemplateView
from .models import *
from inventario.models import Inventario
from ventas.models import *
from .forms import *
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin
# Códigos de barras
import barcode
from barcode import get
from barcode.writer import ImageWriter
from django.http import HttpResponse
from io import BytesIO
import json
from datetime import date
import logging
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
import locale
from django.utils.timezone import now
from django.forms import inlineformset_factory
from django.db.models.functions import ExtractMonth
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Prefetch, OuterRef, Exists
from django.db.models import Max
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import requests
import math

# Configuración del logger
logger = logging.getLogger(__name__)

def generar_codigo_barras(request, codigo_barras):
    """
    Genera una imagen PNG del código de barras para el código proporcionado,
    utilizando el estándar EAN-13.
    """
    try:
        codigo_barras_class = barcode.get('ean13', codigo_barras, writer=ImageWriter())
        buffer = BytesIO()
        codigo_barras_class.write(buffer)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='image/png')
    except barcode.errors.BarcodeError as e:
        return HttpResponse(f"Error al generar el código de barras: {str(e)}", status=400)

def generar_codigo_barras_talla(request, producto_talla_id):
    """
    Genera la imagen PNG del código de barras para la variante de producto (ProductoTalla)
    identificada por producto_talla_id.
    """
    producto_talla = get_object_or_404(ProductoTalla, pk=producto_talla_id)
    if not producto_talla.codigo_barras:
        return HttpResponse("La variante no tiene un código de barras asignado.", status=404)
    return generar_codigo_barras(request, producto_talla.codigo_barras)

def index(request):
    categorias = Categoria.objects.all()

    # Prefetch ajustado para obtener tallas activas por producto
    productos = Producto.objects.filter(catalogo='catalogo').prefetch_related(
        Prefetch(
            'producto_tallas',
            queryset=ProductoTalla.objects.filter(activa=True),
            to_attr='tallas_activas'  # Tallas activas específicas del producto
        )
    )

    # Obtener el precio máximo de los productos disponibles
    precio_maximo_producto = productos.aggregate(Max('precio_venta'))['precio_venta__max']

    # Recuperar parámetros con valores por defecto
    categoria_id = request.GET.get('category')
    price_min = request.GET.get('price_min', 0)
    price_max = request.GET.get('price_max', precio_maximo_producto)
    en_oferta = request.GET.get('en_oferta')
    genero = request.GET.get('genero')
    talla = request.GET.get('talla')
    color = request.GET.get('color')
    order_by = request.GET.get('order_by', 'nombre')

    # Aplicar filtros
    if categoria_id:
        categoria = get_object_or_404(Categoria, id=categoria_id)
        productos = productos.filter(categoria=categoria)

    if price_min is not None:
        productos = productos.filter(precio_venta__gte=float(price_min))

    if price_max is not None:
        productos = productos.filter(precio_venta__lte=float(price_max))

    if en_oferta:
        productos = productos.filter(en_oferta=True)

    if genero in ['dama', 'caballero', 'unisex']:
        productos = productos.filter(producto_tallas__genero=genero, producto_tallas__activa=True)

    if talla:
        productos = productos.filter(producto_tallas__talla__nombre=talla, producto_tallas__activa=True)

    if color:
        productos = productos.filter(producto_tallas__color__iexact=color, producto_tallas__activa=True)

    productos = productos.order_by(order_by)

    # Paginación
    paginator = Paginator(productos, 20)
    page = request.GET.get('page')
    try:
        productos_paginados = paginator.page(page)
    except PageNotAnInteger:
        productos_paginados = paginator.page(1)
    except EmptyPage:
        productos_paginados = paginator.page(paginator.num_pages)

    # Obtener tallas y colores únicos disponibles
    tallas_disponibles = Talla.objects.filter(
        producto_tallas__producto__in=productos,
        producto_tallas__activa=True
    ).distinct()

    colores_disponibles = ProductoTalla.objects.filter(
        producto__in=productos,
        activa=True
    ).values_list('color', flat=True).distinct()

    return render(request, 'index.html', {
        'categorias': categorias,
        'productos': productos_paginados,
        'precio_maximo_producto': precio_maximo_producto,
        'tallas_disponibles': tallas_disponibles,
        'colores_disponibles': colores_disponibles,
    })


# Vista para la página de "Ubícanos"
def ubicanos(request):
    return render(request, 'ubicanos.html')

# Vista del dashboard para el gerente
@login_required
def dashboard_gerente(request):
    # Obtener fecha actual
    today = now()
    current_date = today.date()
    current_year = today.year
    current_month = today.month

    # Ventas diarias (fecha actual)
    ventas_del_dia = Venta.objects.filter(fecha__date=current_date)
    total_ventas_dia = ventas_del_dia.aggregate(total=Sum('total'))['total'] or 0
    cantidad_ventas_dia = ventas_del_dia.count()

    # Ventas agrupadas por mes del año actual
    ventas_por_mes = Venta.objects.filter(fecha__year=current_year) \
        .annotate(month=ExtractMonth('fecha')) \
        .values('month') \
        .annotate(total=Sum('total')) \
        .order_by('month')

    # Inicializar datos mensuales con 0 para los 12 meses
    ventas_mensuales = {i: 0 for i in range(1, 13)}
    for venta in ventas_por_mes:
        ventas_mensuales[venta['month']] = venta['total']

    # Calcular totales y diferencias
    total_ventas_mes_actual = ventas_mensuales.get(current_month, 0)
    mes_anterior = current_month - 1 if current_month > 1 else 12
    total_ventas_mes_anterior = ventas_mensuales.get(mes_anterior, 0)

    if total_ventas_mes_anterior > 0:
        porcentaje_diferencia = ((total_ventas_mes_actual - total_ventas_mes_anterior) / total_ventas_mes_anterior) * 100
    elif total_ventas_mes_actual > 0:
        porcentaje_diferencia = 100
    else:
        porcentaje_diferencia = 0

    # Productos con bajo inventario (considerando tallas)
    productos_bajo_stock = Producto.objects.filter(producto_tallas__cantidad__lte=5).distinct()

    # Productos sin inventario (considerando tallas)
    productos_sin_stock = Producto.objects.filter(producto_tallas__cantidad=0).distinct()

    # Total de ventas del mes actual y cantidad de ventas realizadas
    cantidad_ventas_mes_actual = Venta.objects.filter(fecha__year=current_year, fecha__month=current_month).count()

    # Pasar datos al contexto
    context = {
        'total_ventas_dia': total_ventas_dia,
        'cantidad_ventas_dia': cantidad_ventas_dia,
        'total_ventas_mes_actual': total_ventas_mes_actual,
        'total_ventas_mes_anterior': total_ventas_mes_anterior,
        'porcentaje_diferencia': round(porcentaje_diferencia, 2),
        'cantidad_ventas_mes_actual': cantidad_ventas_mes_actual,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_sin_stock': productos_sin_stock,
        'ventas_mensuales': ventas_mensuales,
        'show_sidebar': True,
    }

    return render(request, 'dashboard/dashboard_gerente.html', context)

def obtener_datos_ventas(request):
    año = int(request.GET.get('año', date.today().year))

    # Ventas agrupadas por mes
    ventas_por_mes = Venta.objects.filter(fecha__year=año) \
        .annotate(month=ExtractMonth('fecha')) \
        .values('month') \
        .annotate(total=Sum('total')) \
        .order_by('month')

    # Nombres de meses en español
    nombres_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    monthly_labels = nombres_meses
    monthly_values = [0] * 12  # Inicia con 0 para cada mes

    for venta in ventas_por_mes:
        monthly_values[venta['month'] - 1] = venta['total']

    # Productos más vendidos
    productos_mas_vendidos = DetalleVenta.objects.filter(venta__fecha__year=año) \
        .values('producto_talla__producto__nombre') \
        .annotate(total_vendido=Sum('cantidad')) \
        .order_by('-total_vendido')[:5]

    productos_labels = [p['producto_talla__producto__nombre'] for p in productos_mas_vendidos]
    productos_values = [p['total_vendido'] for p in productos_mas_vendidos]

    data = {
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'productos_labels': productos_labels,
        'productos_values': productos_values,
        'current_year': año,
        'years': list(range(2020, date.today().year + 1)),  # Años disponibles
    }
    return JsonResponse(data)

# Vista del dashboard para el vendedor
@login_required
def dashboard_vendedor(request):
    # Forzar español Colombia
    locale.setlocale(locale.LC_TIME, 'es_CO.UTF-8')

    # Obtener todos los productos y ventas
    productos = Producto.objects.all()
    ventas = Venta.objects.all()

    # Filtrar productos con bajo stock (cantidad <= 5) y sin stock (cantidad == 0)

    # Obtener la fecha actual
    today = timezone.now()  # Obtener la fecha y hora actual
        # Consultar las ventas agrupadas por mes del año actual

    monthly_data = ventas.filter(fecha__year=today.year) \
        .extra(select={'month': "strftime('%%m', fecha)"}) \
        .values('month') \
        .annotate(total=Sum('total')) \
        .order_by('month')

    # Nombres de meses en español
    nombres_meses = {
        '01': "Enero", '02': "Febrero", '03': "Marzo", '04': "Abril", '05': "Mayo", '06': "Junio",
        '07': "Julio", '08': "Agosto", '09': "Septiembre", '10': "Octubre", '11': "Noviembre", '12': "Diciembre"
    }
        # Inicializa listas con 0 para cada mes
    monthly_values = {str(i).zfill(2): 0 for i in range(1, 13)}  # Diccionario con 0 para cada mes

    # Rellenar los valores con los datos reales de ventas
    for data in monthly_data:
        month = data['month']  # Mes como string '01', '02', ..., '12'
        total = data['total'] or 0  # Total de ventas del mes (0 si no hay ventas)
        monthly_values[month] = total  # Asigna el total de ventas al mes correspondiente

    # Obtener el mes actual y mes pasado
    mes_actual = today.month
    mes_pasado = mes_actual - 1 if mes_actual > 1 else 12  # Si es enero, el mes pasado es diciembre

    # Obtener los totales de ventas para los meses actual y pasado
    total_ventas_mes_actual = monthly_values[str(mes_actual).zfill(2)]  # Ventas del mes actual

        # Cantidad de ventas realizadas este mes
    cantidad_ventas_mes_actual = ventas.filter(fecha__year=today.year, fecha__month=mes_actual).count()

    # Pasar las variables al contexto para renderizar en el template
    context = {
        'productos': productos,
        'ventas': ventas,
        'total_ventas_mes_actual': total_ventas_mes_actual,
        'cantidad_ventas_mes_actual': cantidad_ventas_mes_actual,
        'mes_actual': nombres_meses[str(mes_actual).zfill(2)],  # Mes actual en formato legible
        'mes_pasado': nombres_meses[str(mes_pasado).zfill(2)],  # Mes pasado en formato legible
        'show_sidebar': True,  # Para mostrar la barra lateral
    }

    return render(request, 'dashboard/dashboard_vendedor.html', context)

# Vista para el contenido de productos
class ProductoContenidoView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'dashboard/productos/productos_contenido.html'
    context_object_name = 'productos'
    paginate_by = 10  # Número de resultados por página

    def get_queryset(self):
        queryset = Producto.objects.all()
        search_query = self.request.GET.get('q', '')
        category_id = self.request.GET.get('categoria', '')
        proveedor_id = self.request.GET.get('proveedor', '')
        order_dir = self.request.GET.get('order_dir', 'desc')  # 'desc' por defecto

        if search_query:
            queryset = queryset.filter(nombre__icontains=search_query)
        if category_id:
            queryset = queryset.filter(categoria_id=category_id)
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)

        # Ordenar por los más recientes primero (por ID descendente)
        queryset = queryset.order_by('-id')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        context['proveedores'] = Proveedor.objects.all()

        productos = context['productos']
        for producto in productos:
            # Todas las combinaciones de talla, color, género y cantidad del producto
            producto.variantes = ProductoTalla.objects.filter(
                producto=producto,
                cantidad__gt=0
            ).select_related('talla')

        return context

# Formset para crear
ProductoTallaCreateFormSet = inlineformset_factory(
    Producto,
    ProductoTalla,
    form=ProductoTallaForm,
    extra=1,
    can_delete=False  # opcional en crear
)

# Formset para editar
ProductoTallaEditFormSet = inlineformset_factory(
    Producto,
    ProductoTalla,
    form=ProductoTallaForm,
    extra=1,
    can_delete=True
)
class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'dashboard/productos/crear_producto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Usamos self.object si ya existe; de lo contrario pasamos None
        instance = self.object if hasattr(self, 'object') and self.object is not None else None
        
        if self.request.POST:
            context['formset'] = ProductoTallaCreateFormSet(self.request.POST, instance=instance)
        else:
            context['formset'] = ProductoTallaCreateFormSet(instance=instance)
            
        # Obtener todas las tallas para ser usadas en el formset o en filtros en el template
        context['tallas'] = Talla.objects.all()
        
        # Armar diccionario con cantidad existente para cada talla si se está editando un producto.
        if instance:
            context['tallas_con_cantidad'] = {
                talla.id: ProductoTalla.objects.filter(producto=instance, talla=talla).first().cantidad
                if ProductoTalla.objects.filter(producto=instance, talla=talla).exists()
                else 0
                for talla in Talla.objects.all()
            }
        else:
            context['tallas_con_cantidad'] = {talla.id: 0 for talla in Talla.objects.all()}
        
        # Pasar errores, si existen, al contexto para mostrarlos (por ejemplo, en un modal o alerta)
        if hasattr(self, 'form_errors'):
            context['form_errors'] = self.form_errors
        
        # Variables para mostrar modales de éxito o error en la plantilla
        context['show_success_modal'] = getattr(self, 'show_success_modal', False)
        context['show_error_modal'] = getattr(self, 'show_error_modal', False)
        
        return context

    def form_valid(self, form):
        # Intentamos guardar el producto y capturamos errores de validación (por ejemplo, nombre duplicado)
        try:
            self.object = form.save()
        except ValidationError as e:
            for field, error_list in e.message_dict.items():
                for error in error_list:
                    form.add_error(field, error)
            # Además, se pueden registrar los errores en self.form_errors si deseas procesarlos en el template
            self.form_errors = form.errors
            self.show_error_modal = True
            return self.form_invalid(form)
            
        # Una vez guardado el producto principal, trabajamos con el formset
        formset = ProductoTallaEditFormSet(self.request.POST, instance=self.object)
        if formset.is_valid():
            formset.save()
            messages.success(self.request, "Producto creado exitosamente.")
            return redirect(self.get_success_url())
        else:
            self.form_errors = formset.errors
            self.show_error_modal = True
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_invalid(self, form):
        # En caso de error en el formulario principal, se carga el formset con la data ingresada
        formset = ProductoTallaEditFormSet(self.request.POST, instance=self.object)
        self.form_errors = form.errors
        self.show_error_modal = True
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get_success_url(self):
        return reverse_lazy('contenido_productos')

class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'dashboard/productos/editar_producto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ProductoTallaEditFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['formset'] = ProductoTallaEditFormSet(instance=self.object)

        context['tallas'] = Talla.objects.all()
        producto_tallas = ProductoTalla.objects.filter(producto=self.object).select_related('talla')
        tallas_con_cantidad = {talla.id: 0 for talla in Talla.objects.all()}
        for pt in producto_tallas:
            tallas_con_cantidad[pt.talla.id] = pt.cantidad
        context['tallas_con_cantidad'] = tallas_con_cantidad

        context['form_errors'] = getattr(self, 'form_errors', None)

        image_fields = ['imagen1', 'imagen2', 'imagen3', 'imagen4', 'imagen5']
        image_data = {field: getattr(self.object, field, None) for field in image_fields}
        context['image_fields'] = image_fields
        context['image_data'] = image_data

        context['show_success_modal'] = getattr(self, 'show_success_modal', False)
        context['show_error_modal'] = getattr(self, 'show_error_modal', False)

        return context

    def form_valid(self, form):
        self.object = form.save()
        formset = ProductoTallaEditFormSet(self.request.POST, self.request.FILES, instance=self.object)

        if formset.is_valid():
            formset.save()
            messages.success(self.request, "Producto actualizado exitosamente.")
            self.show_success_modal = True
            return redirect(self.get_success_url())
        else:
            print("Errores del formset:", formset.errors)
            self.form_errors = formset.errors
            self.show_error_modal = True
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_invalid(self, form):
        formset = ProductoTallaEditFormSet(self.request.POST, self.request.FILES, instance=self.object)
        self.form_errors = form.errors
        self.show_error_modal = True
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get_success_url(self):
        return reverse_lazy('contenido_productos')

class ProductoDeleteView(LoginRequiredMixin, DeleteView):
    model = Producto
    template_name = 'dashboard/productos/eliminar_producto.html'
    
    def get_success_url(self):
        return reverse_lazy('contenido_productos') 

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        if request.is_ajax():
            return JsonResponse({'success': True, 'message': 'Producto eliminado exitosamente.'})
        return response

class ProductDetailView(LoginRequiredMixin, DetailView):
    """
    Vista de detalle de un producto.
    Muestra la información completa del producto especificado por su pk.
    """
    model = Producto
    template_name = "dashboard/productos/detalles_producto.html"
    context_object_name = "producto"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto = self.object

        # Tallas disponibles con cantidad > 0
        tallas_disponibles = ProductoTalla.objects.filter(
            producto=producto,
            cantidad__gt=0
        ).select_related('talla', 'color')

        # Colores únicos disponibles (por cantidad > 0)
        colores_disponibles = (
            tallas_disponibles
            .values('color__nombre', 'color__codigo_hex')
            .distinct()
        )

        # Géneros únicos disponibles (por cantidad > 0)
        generos_disponibles = (
            tallas_disponibles
            .values_list('genero', flat=True)
            .distinct()
        )

        context["tallas_disponibles"] = tallas_disponibles
        context["colores_disponibles"] = colores_disponibles
        context["generos_disponibles"] = generos_disponibles

        return context

class ProductDetailShopView(DetailView):
    model = Producto
    template_name = 'tienda/detalles_producto_tienda.html'
    context_object_name = 'producto'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Solo mostramos productos que están en catálogo.
        return Producto.objects.filter(catalogo='catalogo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto = self.object

        # Lista de imágenes adicionales del producto
        imagenes_adicionales = [
            producto.imagen2,
            producto.imagen3,
            producto.imagen4,
            producto.imagen5,
        ]
        # Filtramos las imágenes vacías o nulas
        context['imagenes_adicionales'] = [img for img in imagenes_adicionales if img]

        # Productos similares (filtramos también que estén en catálogo)
        context['productos_similares'] = Producto.objects.filter(
            categoria=producto.categoria,
            catalogo='catalogo'
        ).exclude(id=producto.id)[:4]

        # Tallas disponibles únicas con cantidad > 0
        tallas_disponibles = ProductoTalla.objects.filter(
            producto=producto,
            cantidad__gt=0
        ).select_related('talla', 'color').values_list('talla__nombre', flat=True).distinct()

        context["tallas_disponibles"] = tallas_disponibles

        # Para colores y géneros, necesitas la queryset original (no la lista de nombres de tallas)
        variantes_disponibles = ProductoTalla.objects.filter(
            producto=producto,
            cantidad__gt=0
        ).select_related('talla', 'color')

        context["colores_disponibles"] = variantes_disponibles.values(
            'color__nombre', 'color__codigo_hex'
        ).distinct()

        context["generos_disponibles"] = variantes_disponibles.values_list(
            'genero', flat=True
        ).distinct()

        return context


def buscar_productos(request):
    query = request.GET.get('q')
    productos = Producto.objects.all()

    if query:
        productos = productos.filter(nombre__icontains=query)

    context = {
        'productos': productos,
        'query': query,
    }
    return render(request, 'tienda/buscar_productos.html', context)

# Vista para el contenido de categorias
class CategoriaContenidoView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = 'dashboard/categorias/categorias_contenido.html'
    context_object_name = 'categorias'

    def get_queryset(self):
        return Categoria.objects.all()

class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'dashboard/categorias/crear_categoria.html'
    success_url = reverse_lazy('contenido_categorias')

    def form_valid(self, form):
        response = super().form_valid(form)
        return response
    
class CategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'dashboard/categorias/editar_categoria.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Categoría actualizada exitosamente.'})
        return response
    
    def get_success_url(self):
        return reverse('contenido_categorias')

class CategoriaDeleteView(LoginRequiredMixin, DeleteView):
    model = Categoria
    template_name = 'dashboard/categorias/eliminar_categoria.html'
    success_url = '/categorias/'

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        if self.request.is_ajax():
            return JsonResponse({'success': True, 'message': 'Categoría eliminada exitosamente.'})
        return response

# Vista para el contenido de proveedores
class ProveedorContenidoView(LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = 'dashboard/proveedores/proveedores_contenido.html'
    context_object_name = 'proveedores'
    paginate_by = 6

    def get_queryset(self):
        return Proveedor.objects.all()

class ProveedorCreateView(LoginRequiredMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'dashboard/proveedores/crear_proveedor.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        # Verificar si la solicitud es AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Proveedor creado exitosamente.'})
        return response

    # Definir la URL de éxito
    def get_success_url(self):
        return reverse_lazy('contenido_proveedores') 

class ProveedorUpdateView(LoginRequiredMixin, UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'dashboard/proveedores/editar_proveedor.html'

    def form_valid(self, form):
        messages.success(self.request, '¡Proveedor actualizado correctamente!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('contenido_proveedores')

class ProveedorDeleteView(LoginRequiredMixin, DeleteView):
    model = Proveedor  
    template_name = 'dashboard/proveedores/eliminar_proveedor.html'

    def get_success_url(self):
        return reverse_lazy('contenido_proveedores')  # Redirige a la vista que lista los proveedores

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        if self.request.is_ajax():
            return JsonResponse({'success': True, 'message': 'Proveedor eliminado exitosamente.'})
        return response


def productos_vendidos_hoy(request):
    hoy = timezone.now().date()
    
    # Obtener productos vendidos hoy
    productos_vendidos = DetalleVenta.objects.filter(venta__fecha__date=hoy).values(
        'producto_talla__producto__nombre'
    ).annotate(
        total_cantidad=Sum('cantidad'), 
        total_venta=Sum('total')
    )
    
    # Obtener total de ventas por método de pago
    metodos_pago = Venta.objects.filter(fecha__date=hoy).values("metodo_pago").annotate(total=Sum("total"))
    
    # Convertir datos a formato JSON
    productos = [{
        'nombre': item['producto_talla__producto__nombre'],
        'cantidad': int(item['total_cantidad']),
        'total': int(item['total_venta'])
    } for item in productos_vendidos]

    metodos_pago_dict = {item['metodo_pago']: int(item['total']) for item in metodos_pago}

    total_ventas = sum(metodos_pago_dict.values())

    return JsonResponse({
        'success': True,
        'productos': productos,
        'total_ventas': total_ventas,
        'metodos_pago': metodos_pago_dict
    })

# Vista para imprimir códigos de barras
def imprimir_codigos_barras(request):
    if request.method == 'POST':
        # Se obtienen los códigos seleccionados y se repiten según la cantidad solicitada.
        selected_codes = request.POST.getlist('codigos[]')
        codigos_final = []
        for code in selected_codes:
            qty_str = request.POST.get('cantidad_' + code, '1')
            try:
                qty = int(qty_str)
            except ValueError:
                qty = 1
            codigos_final.extend([code] * qty)

        # Dimensiones de la hoja en puntos (1 cm ≈ 28.35 pts)
        page_width = 5.8 * 28.35    # ~164 pts
        page_height = 20.99 * 28.35  # ~595 pts

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=(page_width, page_height))
        
        # Eliminar márgenes y espaciados
        margin_left = -10
        margin_right = 0
        margin_top = 2      
        margin_bottom = 0   
        horizontal_spacing = 10
        vertical_spacing = 0    
        
        # Calcular el ancho para cada imagen en 2 columnas (sin separación)
        image_width = (page_width - margin_left - margin_right - horizontal_spacing) / 1
        image_height = 80  # Altura fija para cada imagen (ajústala según necesites)
        
        # Calcular la cantidad máxima de filas que caben en una hoja
        max_rows = math.floor((page_height - margin_top - margin_bottom + vertical_spacing) / (image_height + vertical_spacing))
        
        current_index = 0
        total_items = len(codigos_final)
        
        while current_index < total_items:
            # Imprimir hasta max_rows x 2 imágenes por página
            for row in range(max_rows):
                for col in range(2):
                    if current_index >= total_items:
                        break
                    # Para la primera columna: x = 0; para la segunda: x = image_width
                    x_position = margin_left if col == 0 else margin_left + image_width
                    y_position = page_height - margin_top - image_height - row * (image_height + vertical_spacing)
                    
                    code = codigos_final[current_index]
                    
                    # Obtener URL según el tipo de código
                    if code.startswith("general-"):
                        product_id = code.split("-")[1]
                        barcode_url = request.build_absolute_uri(
                            reverse('codigo_barras_producto', args=[product_id])
                        )
                    elif code.startswith("talla-"):
                        talla_id = code.split("-")[1]
                        barcode_url = request.build_absolute_uri(
                            reverse('codigo_barras_talla', args=[talla_id])
                        )
                    else:
                        current_index += 1
                        continue

                    response = requests.get(barcode_url)
                    if response.status_code == 200:
                        image = ImageReader(BytesIO(response.content))
                        pdf.drawImage(
                            image,
                            x_position,
                            y_position,
                            width=image_width,
                            height=image_height,
                            preserveAspectRatio=False  # Fija la imagen para llenar todo el espacio
                        )
                    current_index += 1
                if current_index >= total_items:
                    break
            if current_index < total_items:
                pdf.showPage()  # Nueva página si quedan códigos

        pdf.save()
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')
    
    return HttpResponse("Método no permitido", status=405)

def eliminar_productos_seleccionados(request):
    if request.method == "POST":
        ids = request.POST.getlist('productos_seleccionados')
        if ids:
            productos_eliminados = Producto.objects.filter(id__in=ids)
            productos_eliminados.delete()
            messages.success(request, f'Se eliminaron {len(ids)} producto(s).')
        else:
            messages.warning(request, 'No seleccionaste ningún producto.')
    return redirect('contenido_productos')


# --- VISTAS CRUD PARA TALLAS ---
class TallaListView(ListView):
    model = Talla
    template_name = 'dashboard/tallas/listar_tallas.html'
    context_object_name = 'tallas'

class TallaCreateView(CreateView):
    model = Talla
    form_class = TallaForm
    template_name = 'dashboard/tallas/crear_talla.html'
    success_url = reverse_lazy('contenido_adicionales')  # Redirige a la vista unificada

class TallaUpdateView(UpdateView):
    model = Talla
    form_class = TallaForm
    template_name = 'dashboard/tallas/editar_talla.html'
    success_url = reverse_lazy('contenido_adicionales')

class TallaDeleteView(DeleteView):
    model = Talla
    template_name = 'dashboard/tallas/eliminar_talla.html'
    success_url = reverse_lazy('contenido_adicionales')

# --- VISTAS CRUD PARA COLORES ---
class ColorListView(ListView):
    model = Color
    template_name = 'dashboard/colores/listar_colores.html'
    context_object_name = 'colores'

class ColorCreateView(CreateView):
    model = Color
    form_class = ColorForm
    template_name = 'dashboard/colores/crear_color.html'
    success_url = reverse_lazy('contenido_adicionales')

class ColorUpdateView(UpdateView):
    model = Color
    form_class = ColorForm
    template_name = 'dashboard/colores/editar_color.html'
    success_url = reverse_lazy('contenido_adicionales')

class ColorDeleteView(DeleteView):
    model = Color
    template_name = 'dashboard/colores/eliminar_color.html'
    success_url = reverse_lazy('contenido_adicionales')

# --- VISTA UNIFICADA ADICIONALES CON TALLAS Y COLORES ---
class AdicionalesListView(TemplateView):
    template_name = 'dashboard/adicionales/adicionales.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tallas'] = Talla.objects.all()
        context['colores'] = Color.objects.all()
        return context