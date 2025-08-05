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
from django.views.decorators.csrf import csrf_exempt
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
from reportlab.lib.pagesizes import portrait, landscape
from reportlab.lib.utils import ImageReader
import requests
import math

# Configuración del logger
logger = logging.getLogger(__name__)

def generar_codigo_barras(request, codigo_barras):
    """
    Genera una imagen PNG del código de barras para el código proporcionado,
    utilizando el estándar EAN-13 con márgenes personalizados para todos los productos,
    y recorta los márgenes laterales.
    """
    try:
        # Genera el código de barras sin recortar (con margen original)
        codigo_barras_class = barcode.get('ean13', codigo_barras, writer=ImageWriter())

        # Establece los márgenes para el código de barras
        codigo_barras_class.writer.set_options({
            'module_height': 15,  # Establece la altura de las barras
            'module_width': 0.3,  # Establece el grosor de las barras
            'quiet_zone': 3,      # Márgenes laterales estándar (se recortarán)
        })

        # Guarda el código de barras en un buffer
        buffer = BytesIO()
        codigo_barras_class.write(buffer)
        buffer.seek(0)

        # Abre la imagen generada con Pillow
        image = Image.open(buffer)

        # Recorta la imagen para eliminar los márgenes laterales
        left, top, right, bottom = image.getbbox()  # Obtiene el bounding box de la imagen
        image = image.crop((left + 60, top, right - 60, bottom))  # Recorta # pixeles de cada lado

        # Guarda la imagen recortada en un buffer
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)

        # Retorna la imagen recortada como respuesta HTTP
        return HttpResponse(output, content_type='image/png')

    except barcode.errors.BarcodeError as e:
        return HttpResponse(f"Error al generar el código de barras: {str(e)}", status=400)

def generar_codigo_barras_talla(request, producto_talla_id):
    """
    Genera la imagen PNG del código de barras para la variante de producto (ProductoTalla)
    identificada por producto_talla_id, aplicando los márgenes ajustados a todos los productos.
    """
    producto_talla = get_object_or_404(ProductoTalla, pk=producto_talla_id)
    if not producto_talla.codigo_barras:
        return HttpResponse("La variante no tiene un código de barras asignado.", status=404)
    return generar_codigo_barras(request, producto_talla.codigo_barras)

@login_required
def actualizar_todos_codigos_barras(request):
    if request.method == 'POST':
        productos_talla = ProductoTalla.objects.all()
        actualizados = []
        errores = []

        for producto_talla in productos_talla:
            try:
                if not producto_talla.codigo_barras:
                    codigo_barras = str(producto_talla.id).zfill(12)  # Ejemplo de código de barras
                    producto_talla.codigo_barras = codigo_barras
                    producto_talla.save()

                actualizados.append({
                    'producto_talla_id': producto_talla.id,
                    'codigo_barras': producto_talla.codigo_barras,
                })
            except Exception as e:
                errores.append({
                    'producto_talla_id': producto_talla.id,
                    'error': str(e)
                })

        return JsonResponse({
            'actualizados': actualizados,
            'errores': errores
        })

    return JsonResponse({'error': 'Método no permitido'}, status=405)

def index(request):
    categorias = Categoria.objects.all()

    # Prefetch para tallas activas
    productos = Producto.objects.filter(catalogo='catalogo').prefetch_related(
        Prefetch(
            'producto_tallas',
            queryset=ProductoTalla.objects.filter(activa=True),
            to_attr='tallas_activas'
        )
    )

    # Precio máximo para filtro
    precio_maximo_producto = productos.aggregate(Max('precio_venta'))['precio_venta__max']

    # Filtros desde GET
    categoria_id = request.GET.get('category')
    price_min = float(request.GET.get('price_min', 0))
    price_max = float(request.GET.get('price_max', precio_maximo_producto))
    en_oferta = request.GET.get('en_oferta')
    genero = request.GET.get('genero')
    talla = request.GET.get('talla')
    color = request.GET.get('color')
    order_by = request.GET.get('order_by', 'nombre')

    # Aplicar filtros
    if categoria_id:
        categoria = get_object_or_404(Categoria, id=categoria_id)
        productos = productos.filter(categoria=categoria)

    productos = productos.filter(precio_venta__gte=price_min, precio_venta__lte=price_max)

    if en_oferta:
        productos = productos.filter(en_oferta=True)

    if genero in ['dama', 'caballero', 'unisex']:
        productos = productos.filter(producto_tallas__genero=genero, producto_tallas__activa=True)

    if talla:
        productos = productos.filter(producto_tallas__talla__nombre=talla, producto_tallas__activa=True)

    if color:
        productos = productos.filter(
            producto_tallas__color__nombre__iexact=color,
            producto_tallas__activa=True
        )

    productos = productos.order_by(order_by)

    # Agregar géneros únicos y manejar imágenes
    for producto in productos:
        generos = set()
        for variante in getattr(producto, "tallas_activas", []):
            if variante.genero:
                generos.add(variante.genero.lower())
        producto.generos_disponibles = generos

    # Paginación
    paginator = Paginator(productos, 20)
    page = request.GET.get('page')
    try:
        productos_paginados = paginator.page(page)
    except PageNotAnInteger:
        productos_paginados = paginator.page(1)
    except EmptyPage:
        productos_paginados = paginator.page(paginator.num_pages)

    # Tallas y colores únicos
    tallas_disponibles = Talla.objects.filter(
        producto_tallas__producto__in=productos,
        producto_tallas__activa=True
    ).distinct()

    colores_disponibles = Color.objects.filter(
        productotalla__producto__in=productos,
        productotalla__activa=True
    ).distinct()

    return render(request, 'index.html', {
        'categorias': categorias,
        'productos': productos_paginados,
        'precio_maximo_producto': precio_maximo_producto,
        'tallas_disponibles': tallas_disponibles,
        'colores_disponibles': colores_disponibles,
        'order_by': order_by,
    })

# Vista para la página de "Ubícanos"
def ubicanos(request):
    return render(request, 'ubicanos.html')

def obtener_datos_ventas(request):
    año = int(request.GET.get('año', date.today().year))

    # Ventas agrupadas por mes
    ventas_por_mes = Venta.objects.filter(fecha__year=año) \
        .annotate(month=ExtractMonth('fecha')) \
        .values('month') \
        .annotate(total=Sum('total')) \
        .order_by('month')

    nombres_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    monthly_labels = nombres_meses
    monthly_values = [0] * 12

    for venta in ventas_por_mes:
        monthly_values[venta['month'] - 1] = venta['total']

    # Productos más vendidos
    productos_mas_vendidos = DetalleVenta.objects.filter(venta__fecha__year=año) \
        .values('producto_talla__producto__nombre') \
        .annotate(total_vendido=Sum('cantidad')) \
        .order_by('-total_vendido')[:5]

    productos_labels = [p['producto_talla__producto__nombre'] for p in productos_mas_vendidos]
    productos_values = [p['total_vendido'] for p in productos_mas_vendidos]

    # Mejor vendedor (empleado con mayor total de ventas)
    mejor_vendedor_data = Venta.objects.filter(fecha__year=año) \
        .values('empleado__first_name', 'empleado__last_name') \
        .annotate(total_ventas=Sum('total')) \
        .order_by('-total_ventas') \
        .first()

    if mejor_vendedor_data:
        mejor_vendedor = f"{mejor_vendedor_data['empleado__first_name']} {mejor_vendedor_data['empleado__last_name']}"
        total_mejor_vendedor = mejor_vendedor_data['total_ventas']
    else:
        mejor_vendedor = "Ninguno"
        total_mejor_vendedor = 0

    data = {
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'productos_labels': productos_labels,
        'productos_values': productos_values,
        'mejor_vendedor': mejor_vendedor,
        'total_mejor_vendedor': total_mejor_vendedor,
        'current_year': año,
        'years': list(range(2020, date.today().year + 1)),
    }
    return JsonResponse(data)

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

        # Variantes para cada producto
        productos = context['productos']
        for producto in productos:
            producto.variantes = ProductoTalla.objects.filter(
                producto=producto,
                cantidad__gt=0
            ).select_related('talla')

        # Construye la querystring con todos los parámetros menos 'page'
        params = self.request.GET.copy()
        if 'page' in params:
            params.pop('page')
        context['query_params'] = params.urlencode()

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
    # Partimos de todos los productos en catálogo
    productos = Producto.objects.filter(catalogo='catalogo')

    if query:
        # Además filtramos por nombre si hay término de búsqueda
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

def imprimir_codigos_view(request):
    q         = request.GET.get('q', '').strip()
    cat_id    = request.GET.get('categoria', '')
    barcode_q = request.GET.get('barcode', '').strip()

    # Base: todos los productos
    productos_list = Producto.objects.all()

    # Filtrar por nombre o referencia
    if q:
        productos_list = (
            productos_list.filter(nombre__icontains=q) |
            productos_list.filter(referencia__icontains=q)
        )

    # Filtrar por categoría
    if cat_id.isdigit():
        productos_list = productos_list.filter(categoria_id=cat_id)

    # Filtrar por código de barras en sus variantes
    if barcode_q:
        productos_list = productos_list.filter(
            producto_tallas__codigo_barras__icontains=barcode_q
        ).distinct()

    productos_list = productos_list.order_by('nombre')

    # Paginación
    paginator = Paginator(productos_list, 20)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # Construir query_params con todos los GET menos 'page'
    params = request.GET.copy()
    if 'page' in params:
        params.pop('page')
    query_params = params.urlencode()

    context = {
        'productos': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'q': q,
        'categories': Categoria.objects.all().order_by('nombre'),
        'selected_cat': cat_id,
        'barcode_q': barcode_q,
        'query_params': query_params,
    }
    return render(request, 'dashboard/productos/imprimir_codigos.html', context)

def imprimir_codigos_barras(request):
    if request.method != 'POST':
        return JsonResponse({"mensaje": "Método no permitido"}, status=405)

    # 1. Leer inputs
    codigos    = request.POST.getlist('codigos[]')
    cantidades = request.POST.getlist('cantidades[]')
    img_urls   = request.POST.getlist('img_urls[]')

    # 2. Construir lista de URLs según cantidad
    images_to_print = []
    for _, qty, url in zip(codigos, cantidades, img_urls):
        try:
            q = int(qty)
        except ValueError:
            q = 1
        images_to_print += [url] * max(1, q)

    if not images_to_print:
        return JsonResponse({"mensaje": "No se recibieron códigos de barras para imprimir"}, status=400)

    # 3. Definir dimensiones (mm → pt)
    mm_to_pt   = 2.834645669
    w_label_mm = 75
    h_label_mm = 49
    w_label = w_label_mm * mm_to_pt
    h_label = h_label_mm * mm_to_pt

    # 4. Tamaño total de página: 2×2 etiquetas
    page_size = (2 * w_label, 2 * h_label)   # 150×98 mm
    buffer = BytesIO()

    # 5. Crear canvas forzando siempre landscape
    pdf = canvas.Canvas(buffer, pagesize=landscape(page_size))
    page_w, page_h = pdf._pagesize

    # 6. Dibujar las imágenes en 2 columnas × 2 filas
    total = len(images_to_print)
    idx   = 0
    cols, rows = 2, 2

    while idx < total:
        for row in range(rows):
            for col in range(cols):
                if idx >= total:
                    break

                x0 = col * (page_w / cols)
                y0 = row * (page_h / rows)

                url = images_to_print[idx]
                try:
                    resp = requests.get(url)
                    resp.raise_for_status()
                    img = ImageReader(BytesIO(resp.content))
                    pdf.drawImage(
                        img,
                        x0, y0,
                        width=page_w/cols,
                        height=page_h/rows,
                        preserveAspectRatio=True,
                        anchor='sw'
                    )
                except Exception as e:
                    print(f"Error procesando imagen {url}: {e}")

                idx += 1

        if idx < total:
            pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')
