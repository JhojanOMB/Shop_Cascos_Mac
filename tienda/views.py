from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.views.generic import ListView, UpdateView, DeleteView, CreateView, DetailView, TemplateView
from .models import *
from inventario.models import Inventario
from ventas.models import *
from .forms import *
from django.http import JsonResponse, HttpResponseRedirect, HttpRequest, HttpResponse
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

def _get_reverse_accessor_name(from_model, target_model_name):
    """
    Devuelve el accessor inverso en `from_model` que apunta a `target_model_name`.
    Ej: en Producto buscar el related object que apunta a ProductoTalla y devolver su accessor.
    Retorna None si no lo encuentra.
    """
    try:
        for rel in from_model._meta.related_objects:
            try:
                if rel.related_model.__name__.lower() == target_model_name.lower():
                    return rel.get_accessor_name()
            except Exception:
                continue
    except Exception:
        pass
    return None


def index(request: HttpRequest) -> HttpResponse:
    categorias = Categoria.objects.all()

    # Base: solo productos en catálogo (ajusta si tu campo/catalogo difiere)
    productos_qs = Producto.objects.filter(catalogo='catalogo').distinct()

    # Detectar accessors inversos de forma robusta
    producto_to_talla_accessor = _get_reverse_accessor_name(Producto, 'ProductoTalla') or 'producto_tallas'
    talla_to_talla_accessor = _get_reverse_accessor_name(Talla, 'ProductoTalla') or 'productotalla_set'

    # Comprobar si Producto tiene campo 'activa' (evitar FieldError)
    producto_tiene_activa = True
    try:
        Producto._meta.get_field('activa')
    except Exception:
        producto_tiene_activa = False

    # Comprobar si ProductoTalla tiene campo 'activa' (para lookups relacionados)
    productotalla_tiene_activa = True
    try:
        ProductoTalla._meta.get_field('activa')
    except Exception:
        productotalla_tiene_activa = False

    # Query base de productos (si existe campo 'activa' lo aplicamos, sino no)
    if producto_tiene_activa:
        productos = Producto.objects.filter(activa=True)
    else:
        productos = Producto.objects.all()

    # Intentamos prefetch de variantes activas y color usando el accessor detectado.
    try:
        # Si ProductoTalla tiene 'activa', prefetch solo activas, sino prefetch todo
        if productotalla_tiene_activa:
            prefetch_variantes = Prefetch(producto_to_talla_accessor, queryset=ProductoTalla.objects.filter(activa=True).select_related('color'))
        else:
            prefetch_variantes = Prefetch(producto_to_talla_accessor, queryset=ProductoTalla.objects.select_related('color'))
        productos = productos.prefetch_related(prefetch_variantes)
        productos_qs = productos_qs.prefetch_related(prefetch_variantes)
    except Exception:
        # fallback a nombre conocido
        try:
            productos = productos.prefetch_related('producto_tallas__color')
            productos_qs = productos_qs.prefetch_related('producto_tallas__color')
        except Exception:
            pass

    # precio máximo (proteger None)
    precio_maximo_producto = productos_qs.aggregate(Max('precio_venta'))['precio_venta__max'] or 0

    # parámetros de filtrado
    categoria_id = request.GET.get('category') or None
    price_min = request.GET.get('price_min') or None
    price_max = request.GET.get('price_max') or None
    en_oferta = request.GET.get('en_oferta')
    genero = request.GET.get('genero')
    talla = request.GET.get('talla')
    color = request.GET.get('color')
    order_by = request.GET.get('orden') or 'nombre'

    # empezamos con la queryset filtrable
    qs = productos_qs

    # filtros simples
    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)

    if price_min:
        try:
            qs = qs.filter(precio_venta__gte=float(price_min))
        except (ValueError, TypeError):
            pass

    if price_max:
        try:
            qs = qs.filter(precio_venta__lte=float(price_max))
        except (ValueError, TypeError):
            pass

    if en_oferta:
        qs = qs.filter(en_oferta=True)

    # Filtros sobre la relación ProductoTalla usando el accessor detectado
    # Añadimos __activa solo si ProductoTalla realmente tiene ese campo
    if genero in ['dama', 'caballero', 'unisex']:
        lookup = {
            f"{producto_to_talla_accessor}__genero": genero,
        }
        if productotalla_tiene_activa:
            lookup[f"{producto_to_talla_accessor}__activa"] = True
        try:
            qs = qs.filter(**lookup)
        except Exception:
            pass

    if talla:
        lookup = {f"{producto_to_talla_accessor}__talla__nombre": talla}
        if productotalla_tiene_activa:
            lookup[f"{producto_to_talla_accessor}__activa"] = True
        try:
            qs = qs.filter(**lookup)
        except Exception:
            pass

    if color:
        try:
            lookup = {f"{producto_to_talla_accessor}__color__nombre__iexact": color}
            if productotalla_tiene_activa:
                lookup[f"{producto_to_talla_accessor}__activa"] = True
            qs = qs.filter(**lookup)
        except Exception:
            # fallback si color fuera campo texto
            try:
                lookup = {f"{producto_to_talla_accessor}__color__iexact": color}
                if productotalla_tiene_activa:
                    lookup[f"{producto_to_talla_accessor}__activa"] = True
                qs = qs.filter(**lookup)
            except Exception:
                pass

    # ordenar (proteger de un order_by inválido)
    try:
        qs = qs.order_by(order_by)
    except Exception:
        qs = qs.order_by('nombre')

    # paginación
    paginator = Paginator(qs.distinct(), 20)
    page = request.GET.get('page', 1)
    try:
        productos_paginados = paginator.page(page)
    except PageNotAnInteger:
        productos_paginados = paginator.page(1)
    except EmptyPage:
        productos_paginados = paginator.page(paginator.num_pages)

    # Construir colores_por_producto sólo para los productos en la página actual (más eficiente)
    colores_por_producto = {}
    try:
        current_products = list(productos_paginados.object_list)
        for p in current_products:
            # Filtrar variantes del producto con stock > 0 (cualquier talla)
            variantes_qs = ProductoTalla.objects.filter(producto=p)

            # Si tu modelo ProductoTalla tiene 'activa' aplicarla
            try:
                ProductoTalla._meta.get_field('activa')
                variantes_qs = variantes_qs.filter(activa=True)
            except Exception:
                pass

            # Asegurarnos de solo las que tienen cantidad > 0 (si el campo existe)
            try:
                ProductoTalla._meta.get_field('cantidad')
                variantes_qs = variantes_qs.filter(cantidad__gt=0)
            except Exception:
                pass

            # Obtener colores únicos (id, nombre, hex) — distinct por color
            colores_qs = variantes_qs.order_by('color__id').values(
                'color__id', 'color__nombre', 'color__codigo_hex'
            ).distinct()

            # Guardar lista (vacía si no hay)
            colores_por_producto[p.id] = list(colores_qs)
    except Exception:
        colores_por_producto = {}

    # tallas disponibles (usar el accessor inverso desde Talla hacia ProductoTalla)
    try:
        lookup = {
            f"{talla_to_talla_accessor}__producto__in": qs,
        }
        if productotalla_tiene_activa:
            lookup[f"{talla_to_talla_accessor}__activa"] = True
        tallas_disponibles = Talla.objects.filter(**lookup).distinct()
    except Exception:
        tallas_disponibles = Talla.objects.all()

    # colores disponibles generales (desde todas las variantes activas dentro del resultado qs)
    try:
        q_col_ids = ProductoTalla.objects.filter(producto__in=qs)
        if productotalla_tiene_activa:
            q_col_ids = q_col_ids.filter(activa=True)
        color_ids = q_col_ids.values_list('color_id', flat=True).distinct()
        colores_disponibles = Color.objects.filter(id__in=[c for c in color_ids if c is not None])
    except Exception:
        colores_disponibles = Color.objects.none()

    context = {
        'categorias': categorias,
        'productos': productos_paginados,
        'precio_maximo_producto': precio_maximo_producto,
        'tallas_disponibles': tallas_disponibles,
        'colores_disponibles': colores_disponibles,
        'colores_por_producto': colores_por_producto,
        'en_oferta': bool(en_oferta),
    }
    return render(request, 'index.html', context)

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



class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'dashboard/productos/crear_producto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # instance aún no existe en create
        instance = None

        # Si es POST, queremos reconstruir el formset con los datos enviados (incluyendo files)
        if self.request.method == 'POST':
            context['formset'] = ProductoTallaCreateFormSet(self.request.POST, self.request.FILES, instance=instance)
        else:
            context['formset'] = ProductoTallaCreateFormSet(instance=instance)

        context['tallas'] = Talla.objects.all()
        # Mapa de tallas a cantidades (vacío en create)
        context['tallas_con_cantidad'] = {t.id: 0 for t in context['tallas']}

        context['form_errors'] = getattr(self, 'form_errors', None)
        context['show_success_modal'] = getattr(self, 'show_success_modal', False)
        context['show_error_modal'] = getattr(self, 'show_error_modal', False)

        return context

    def form_valid(self, form):
        # Guardamos el objeto padre primero
        try:
            self.object = form.save()
        except ValidationError as e:
            # Añadir errores al form y volver a mostrar
            for field, error_list in e.message_dict.items():
                for error in error_list:
                    form.add_error(field, error)
            self.form_errors = form.errors
            self.show_error_modal = True
            return self.form_invalid(form)

        # ahora instanciamos el formset con la instancia ya creada
        formset = ProductoTallaCreateFormSet(self.request.POST, self.request.FILES, instance=self.object)
        if formset.is_valid():
            formset.save()
            messages.success(self.request, "Producto creado exitosamente.")
            self.show_success_modal = True
            return redirect(self.get_success_url())
        else:
            # formset inválido: mostrar errores y dejar el producto guardado (si prefieres deshacer, habría que borrar)
            self.form_errors = formset.errors
            self.show_error_modal = True
            # renderizamos con el form (ya guardado) y el formset inválido para que el usuario corrija
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_invalid(self, form):
        # Si el form padre es inválido, reconstruimos el formset con los datos enviados para no perderlos
        formset = ProductoTallaCreateFormSet(self.request.POST, self.request.FILES)
        self.form_errors = form.errors
        self.show_error_modal = True
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get_success_url(self):
        return reverse_lazy('contenido_productos')

# Formset para editar
ProductoTallaEditFormSet = inlineformset_factory(
    Producto,
    ProductoTalla,
    form=ProductoTallaForm,
    extra=1,
    can_delete=True
)

class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'dashboard/productos/editar_producto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # formset: si es POST reconstruimos con los datos enviados (incluye archivos)
        if self.request.method == 'POST':
            context['formset'] = ProductoTallaEditFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['formset'] = ProductoTallaEditFormSet(instance=self.object)
        context['tallas'] = Talla.objects.all()
        return context

    def form_valid(self, form):
        """
        Guardado principal + manejo manual del formset para evitar unique constraint
        y *reemplazar* valores cuando exista un duplicado.
        """
        # Guardamos cambios básicos del producto primero
        self.object = form.save()

        # Construimos el formset con los datos (incluye can_delete)
        formset = ProductoTallaEditFormSet(self.request.POST, self.request.FILES, instance=self.object)

        # Validamos el formset primero para tener cleaned_data
        if not formset.is_valid():
            self.form_errors = formset.errors
            messages.error(self.request, "Corrige los errores en las variantes.")
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

        # Operación atómica para evitar condiciones de carrera
        with transaction.atomic():
            # 1) Procesar eliminaciones primero (DELETE checked)
            # Usamos cleaned_data para detectar deletions
            for f in formset:
                cd = f.cleaned_data
                if not cd:
                    continue
                if cd.get('DELETE'):
                    inst = f.instance
                    if inst and inst.pk:
                        inst.delete()

            # 2) Ahora procesamos los forms (actualizar/crear) y resolver duplicados
            for f in formset:
                cd = f.cleaned_data
                if not cd:
                    continue
                if cd.get('DELETE'):
                    # ya eliminado arriba
                    continue

                # campos clave (ajusta si tus nombres son distintos)
                talla = cd.get('talla')
                color = cd.get('color')
                genero = cd.get('genero')
                cantidad = cd.get('cantidad') or 0
                # ejemplo: precio si lo tienes en el formset
                precio = cd.get('precio') if 'precio' in cd else None
                activa = cd.get('activa') if 'activa' in cd else None

                if f.instance and f.instance.pk:
                    # Form correspondiente a instancia existente (edición)
                    # Bloqueamos la fila actual
                    current = ProductoTalla.objects.select_for_update().filter(pk=f.instance.pk).first()

                    # Buscamos un posible duplicado distinto (mismo producto+talla+color+genero)
                    dup = ProductoTalla.objects.select_for_update().filter(
                        producto=self.object,
                        talla=talla,
                        color=color,
                        genero=genero
                    ).exclude(pk=f.instance.pk).first()

                    if dup:
                        # REEMPLAZAR: asignamos los valores del formulario al duplicado
                        # (usuario quiere que el valor general se reemplace por lo nuevo)
                        dup.cantidad = cantidad
                        if precio is not None and hasattr(dup, 'precio'):
                            dup.precio = precio
                        if activa is not None and hasattr(dup, 'activa'):
                            dup.activa = activa
                        # actualizar otros campos necesarios...
                        dup.save()
                        # borrar la fila actual (porque duplicó a 'dup' y ya actualizamos allí)
                        if current:
                            current.delete()
                    else:
                        # No hay duplicado: actualizamos la instancia actual
                        if current:
                            current.talla = talla
                            current.color = color
                            current.genero = genero
                            current.cantidad = cantidad
                            if precio is not None and hasattr(current, 'precio'):
                                current.precio = precio
                            if activa is not None and hasattr(current, 'activa'):
                                current.activa = activa
                            current.save()
                        else:
                            # Por seguridad, crearla si no existe
                            ProductoTalla.objects.create(
                                producto=self.object,
                                talla=talla,
                                color=color,
                                genero=genero,
                                cantidad=cantidad,
                                precio=precio if precio is not None else 0,
                                activa=(activa if activa is not None else True)
                            )

                else:
                    # Form NUEVO (sin pk). Buscamos si ya existe una variante igual
                    existing = ProductoTalla.objects.select_for_update().filter(
                        producto=self.object,
                        talla=talla,
                        color=color,
                        genero=genero
                    ).first()

                    if existing:
                        # REEMPLAZAR valor general por lo nuevo (no crear duplicado)
                        existing.cantidad = cantidad
                        if precio is not None and hasattr(existing, 'precio'):
                            existing.precio = precio
                        if activa is not None and hasattr(existing, 'activa'):
                            existing.activa = activa
                        existing.save()
                    else:
                        # crear nuevo
                        ProductoTalla.objects.create(
                            producto=self.object,
                            talla=talla,
                            color=color,
                            genero=genero,
                            cantidad=cantidad,
                            precio=precio if precio is not None else 0,
                            activa=(activa if activa is not None else True)
                        )

        # Mensaje y redirect final
        messages.success(self.request, "Producto actualizado correctamente.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # Reconstruimos formset para mostrar errores en template
        formset = ProductoTallaEditFormSet(self.request.POST, self.request.FILES, instance=self.object)
        self.form_errors = form.errors
        messages.error(self.request, "Corrige los errores del formulario.")
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
    Vista de detalle de un producto para el dash.
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
    q = request.GET.get('q', '').strip()
    productos_qs = Producto.objects.filter(catalogo='catalogo')  # o tu filtro
    if q:
        productos_qs = productos_qs.filter(nombre__icontains=q)

    paginator = Paginator(productos_qs.order_by('-id'), 12)  # 12 por página por ejemplo
    page_num = request.GET.get('page', 1)
    page = paginator.get_page(page_num)

    # construir lista de páginas para mostrar (1, ..., current-2..current+2, ..., last)
    pages = []
    last = paginator.num_pages
    for n in paginator.page_range:
        if n == 1 or n == last or (n >= page.number - 2 and n <= page.number + 2):
            pages.append(n)
        elif pages and pages[-1] != '...':
            pages.append('...')

    context = {
        'productos': page,
        'query': q,
        'page_numbers': pages,
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