from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, UpdateView, DeleteView, CreateView, DetailView
from django.db import transaction
from django.urls import reverse_lazy
from .forms import *
from .models import *
from tienda.models import *
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.forms import inlineformset_factory,  ValidationError
import platform
try:
    import win32print
except ImportError:
    win32print = None
import qrcode
import base64
from django.http import HttpResponse
from io import BytesIO
from django.db.models import Q
from .services import VentaService

# FormSet inline para manejar los detalles de la venta
DetalleVentaFormSet = inlineformset_factory(Venta, DetalleVenta, fields=('producto_talla', 'cantidad'), extra=1)

from django.utils import timezone

class VentaContenidoView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = 'dashboard/ventas/ventas_contenido.html'
    context_object_name = 'ventas'
    paginate_by = 8

    def get_queryset(self):
        user = self.request.user
        queryset = Venta.objects.all()

        # Filtrar por rol del usuario
        if user.rol == 'vendedor':
            queryset = queryset.filter(empleado=user)

        # Filtrar por fecha si hay parámetros en la URL
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        if fecha_inicio and fecha_fin:
            fecha_inicio_dt = timezone.datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_dt = timezone.datetime.strptime(fecha_fin, '%Y-%m-%d') + timezone.timedelta(days=1)
            queryset = queryset.filter(fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt)

        # Ordenar por la última venta primero o por la opción seleccionada
        orden = self.request.GET.get('orden', 'desc')
        if orden == 'asc':
            queryset = queryset.order_by('fecha')
        else:
            queryset = queryset.order_by('-fecha')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rol'] = self.request.user.rol
        context['fecha_inicio'] = self.request.GET.get('fecha_inicio', '')
        context['fecha_fin'] = self.request.GET.get('fecha_fin', '')
        context['orden'] = self.request.GET.get('orden', 'desc')  # Default to 'desc'
        return context

class VentaCreateView(LoginRequiredMixin, CreateView):
    model = Venta
    form_class = VentaForm
    template_name = 'dashboard/ventas/crear_venta.html'
    success_url = reverse_lazy('ventas:contenido_ventas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metodos_pago'] = METODOS_PAGO
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'initial': {'empleado': self.request.user}})
        return kwargs

    def form_valid(self, form):
        try:
            venta = VentaService.crear_venta_con_detalles(
                usuario=self.request.user,
                datos_post=self.request.POST,
                form=form
            )
            messages.success(self.request, f"Venta registrada correctamente. Total: ${venta.total:,}")
            return redirect('ventas:imprimir_factura', venta_id=venta.id)

        except ProductoTalla.DoesNotExist:
            messages.error(self.request, "Uno de los productos no existe.")
            return self.form_invalid(form)

        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        except Exception as e:
            messages.error(self.request, "Ocurrió un error inesperado.")
            return self.form_invalid(form)

def obtener_producto_por_codigo(request):
    codigo_barras = request.GET.get('codigo_barras')
    if not codigo_barras:
        return JsonResponse({
            'success': False,
            'message': 'Debe proporcionar un código de barras.'
        }, status=400)
    
    try:
        producto_talla = ProductoTalla.objects.select_related('producto', 'talla', 'color').get(
            Q(codigo_barras=codigo_barras) | Q(codigo_barras='0' + codigo_barras),
            activa=True
        )
        data = {
            'success': True,
            'producto': {
                'id': producto_talla.id,
                'nombre': producto_talla.producto.nombre,
                'precio': float(producto_talla.producto.precio_venta),
                'stock': producto_talla.cantidad,
                'talla': producto_talla.talla.nombre,
                'color': producto_talla.color.nombre if producto_talla.color else None,
                'genero': producto_talla.get_genero_display(),
            }
        }
    except ProductoTalla.DoesNotExist:
        data = {
            'success': False,
            'message': 'Producto no encontrado o código de barras incorrecto.'
        }
    except Exception as e:
        # Aquí devolvemos el error completo para depurar (solo en desarrollo)
        data = {
            'success': False,
            'message': f'Ocurrió un error al buscar el producto: {str(e)}'
        }
    
    return JsonResponse(data)

class VentaUpdateView(LoginRequiredMixin, UpdateView):
    model = Venta
    form_class = VentaForm
    template_name = 'dashboard/ventas/editar_venta.html'
    success_url = reverse_lazy('ventas:contenido_ventas')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.is_ajax():
            return JsonResponse({'success': True, 'message': 'Venta actualizada exitosamente.'})
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Asegúrate de pasar todos los detalles, incluso los anulados si los quieres mostrar
        # Si solo quieres los activos, filtra por anulado=False
        context['detalles'] = self.object.detalles.all()
        return context

class VentaDeleteView(LoginRequiredMixin, DeleteView):
    model = Venta
    template_name = 'dashboard/ventas/eliminar_venta.html'
    success_url = reverse_lazy('ventas:contenido_ventas')

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        if self.request.is_ajax():
            return JsonResponse({'success': True, 'message': 'Venta eliminada exitosamente.'})
        return response

@require_POST
def facturar_venta(request, venta_id):
    try:
        venta = get_object_or_404(Venta, pk=venta_id)
        if venta.facturado:
            return JsonResponse({'success': False, 'message': 'La venta ya ha sido facturada.'})
        venta.facturado = True
        venta.save()
        return JsonResponse({'success': True, 'message': 'Venta facturada exitosamente.', 'url': f'/ventas/imprimir/{venta_id}/'})
    except Venta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Venta no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

def imprimir_factura(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)

    # Contenido de impresión
    contenido = f"""
    FACTURA N°: {venta.numero_factura}
    Fecha: {venta.fecha.strftime("%d/%m/%Y %H:%M")}
    Cliente: {venta.cliente or "Consumidor Final"}
    ----------------------------------------
    Producto       Cant.   Precio   Total
    ----------------------------------------
    """
    for detalle in detalles:
        contenido += f"{detalle.producto_talla.producto.nombre[:12]:12}  {detalle.cantidad:5}  ${detalle.precio:7.2f}  ${detalle.total:7.2f}\n"

    contenido += f"""
    ----------------------------------------
    TOTAL: ${venta.total:.2f}
    MÉTODO DE PAGO: {venta.get_metodo_pago_display()}
    ----------------------------------------
    GRACIAS POR SU COMPRA
    """

    # Generar código QR
    qr = qrcode.make(f"http://127.0.0.1:8000/ventas/factura/{venta.id}/")
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')

    sistema = platform.system()

    # Si es POST, intentar imprimir
    if request.method == "POST":
        if sistema == "Windows" and win32print:
            try:
                printer_name = win32print.GetDefaultPrinter()
                hprinter = win32print.OpenPrinter(printer_name)
                win32print.StartDocPrinter(hprinter, 1, ("Factura", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, contenido.encode('utf-8'))
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
                win32print.ClosePrinter(hprinter)
                return JsonResponse({'success': True, 'message': 'Factura enviada a la impresora correctamente.'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error al imprimir: {str(e)}'})
        else:
            return JsonResponse({'success': False, 'message': f'La impresión directa solo funciona en Windows. Estás usando: {sistema}'})

    # Si es GET, mostrar vista previa
    return render(request, 'dashboard/ventas/imprimir_factura.html', {
        'venta': venta,
        'detalles': detalles,
        'qr_base64': qr_base64,
        'sistema': sistema
    })


class PublicVentaDetalleView(DetailView):
    model = Venta
    template_name = 'dashboard/ventas/detalle_venta_publica.html'
    slug_field = 'numero_factura'
    slug_url_kwarg = 'numero_factura'
    context_object_name = 'venta'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.get_object()
        context['detalles'] = venta.detalles.all()
        return context


class VentaDetalleView(LoginRequiredMixin, DetailView):
    model = Venta
    template_name = 'dashboard/ventas/detalle_venta.html'
    slug_field = 'numero_factura'
    slug_url_kwarg = 'numero_factura'
    context_object_name = 'venta'

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("No tienes permiso para acceder a esta factura.")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.get_object()
        context['detalles'] = venta.detalles.all()
        return context


@require_POST
def anular_detalle_venta(request, detalle_id):
    detalle = get_object_or_404(DetalleVenta, id=detalle_id)
    if not detalle.anulado:
        detalle.anulado = True
        detalle.save()  # Guarda el detalle ya marcado como anulado

        # Devolver el producto al inventario
        producto_talla = detalle.producto_talla
        producto_talla.cantidad += detalle.cantidad
        producto_talla.save()

        # Recalcular total de la venta
        venta = detalle.venta
        venta.total = sum(d.total for d in venta.detalles.filter(anulado=False))
        venta.save()

        return JsonResponse({'success': True, 'message': 'Producto anulado y devuelto al inventario.'})
    else:
        return JsonResponse({'success': False, 'message': 'Este producto ya está anulado.'})
