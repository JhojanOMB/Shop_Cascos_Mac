from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, UpdateView, DeleteView, CreateView, DetailView, View, RedirectView
from django.db import transaction
from django.urls import reverse_lazy
from .forms import *
from .models import *
from tienda.models import *
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden, FileResponse
from django.views.decorators.http import require_POST
from django.forms import inlineformset_factory,  ValidationError
import platform
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
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
from datetime import date, timedelta

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
        # Deja que UpdateView guarde primero la instancia
        response = super().form_valid(form)

        # Nuevo chequeo de AJAX en Django 4+:
        is_ajax = (
            self.request.headers.get('x-requested-with') == 'XMLHttpRequest'
            or self.request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        )

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': 'Venta actualizada exitosamente.'
            })

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasamos todos los detalles, incluidos los anulados
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

class VentaBorradorContenidoView(DetailView):
    model = VentaBorrador
    template_name = 'dashboard/ventas/venta_borrador.html'

    def get_object(self):
        borrador, _ = VentaBorrador.objects.get_or_create(usuario=self.request.user)
        return borrador

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Lleva al template todas las tallas de productos disponibles
        ctx['producto_tallas'] = ProductoTalla.objects.filter(cantidad__gt=0)
        return ctx

class AgregarDetalleBorrador(View):
    def post(self, request):
        borrador, _ = VentaBorrador.objects.get_or_create(usuario=request.user)
        pt_id = request.POST.get('producto_talla')
        cantidad = request.POST.get('cantidad')

        if not pt_id or not cantidad:
            messages.error(request, "Debes seleccionar un producto y definir una cantidad.")
            return redirect('ventas:venta_borrador')

        try:
            cantidad = int(cantidad)
        except ValueError:
            messages.error(request, "La cantidad debe ser un número válido.")
            return redirect('ventas:venta_borrador')

        DetalleBorrador.objects.update_or_create(
            venta_borrador=borrador,
            producto_talla_id=pt_id,
            defaults={'cantidad': cantidad}
        )
        return redirect('ventas:venta_borrador')

class EditarBorradorView(View):
    def post(self, request):
        borrador = get_object_or_404(VentaBorrador, usuario=request.user)
        pt_id = request.POST.get('producto_talla')
        cantidad = request.POST.get('cantidad')

        if not pt_id or not cantidad:
            messages.error(request, "Debes seleccionar un producto y definir una cantidad.")
            return redirect('ventas:venta_borrador')

        try:
            cantidad = int(cantidad)
        except ValueError:
            messages.error(request, "La cantidad debe ser un número válido.")
            return redirect('ventas:venta_borrador')

        detalle = borrador.detalles.filter(producto_talla_id=pt_id).first()
        if detalle:
            detalle.cantidad = cantidad
            detalle.save()
        else:
            DetalleBorrador.objects.create(
                venta_borrador=borrador,
                producto_talla_id=pt_id,
                cantidad=cantidad
            )
        
        return redirect('ventas:venta_borrador')

class EliminarDetalleBorrador(DeleteView):
    model = DetalleBorrador
    template_name = 'dashboard/ventas/borrador_eliminar.html'
    success_url = reverse_lazy('ventas:venta_borrador')  # <- Redirige a la vista sin usar pk

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.venta_borrador.usuario == request.user:
            self.object.delete()
        return redirect(self.success_url)

class FinalizarVentaFromBorrador(View):
    def post(self, request):
        borrador = get_object_or_404(VentaBorrador, usuario=request.user)
        if not borrador.detalles.exists():
            messages.error(request, "No hay productos en el borrador.")
            return redirect('ventas:venta_borrador')

        # 1) Crear Venta definitiva
        venta = Venta.objects.create(empleado=request.user, metodo_pago=request.POST.get('metodo_pago'))
        total = 0
        # 2) Convertir cada DetalleBorrador en DetalleVenta
        for d in borrador.detalles.all():
            subtotal = d.subtotal()
            DetalleVenta.objects.create(
                venta=venta,
                producto_talla=d.producto_talla,
                cantidad=d.cantidad,
                precio=d.producto_talla.precio,
                total=subtotal
            )
            total += subtotal
        venta.total = total
        venta.save()

        # 3) Limpiar el borrador
        borrador.detalles.all().delete()

        messages.success(request, f"Venta finalizada – total ${total:,}")
        return redirect('ventas:imprimir_factura', venta_id=venta.id)


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
    # Obtén la venta y sus detalles
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)
    sistema = platform.system()

    # Genera el QR en memoria
    qr = qrcode.make(f"Factura {venta.numero_factura}")
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # 1) Si en GET viene ?pdf=1, genera y descarga el PDF
    if request.GET.get('pdf') == '1':
        buf = BytesIO()
        width, height = 58 * mm, 270 * mm
        pdf = canvas.Canvas(buf, pagesize=(width, height))
        y = height - 10 * mm

        # — Logo centrado —
        try:
            logo = ImageReader('img/logo2')  # ajusta la ruta
            logo_w, logo_h = 30 * mm, 12 * mm
            pdf.drawImage(logo,
                          (width - logo_w) / 2,
                          y - logo_h,
                          logo_w,
                          logo_h,
                          mask='auto')
            y -= logo_h + 5 * mm
        except Exception:
            y -= 5 * mm

        # — Cabecera sombreada con nombre —
        pdf.setFillGray(0.9)
        pdf.rect(2 * mm, y - 5 * mm, width - 4 * mm, 8 * mm, fill=1, stroke=0)
        pdf.setFillGray(0)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, y, "CASCOS MAC")
        y -= 10 * mm

        # — Línea punteada separadora —
        pdf.setLineWidth(0.3)
        pdf.setDash(1, 2)
        pdf.line(2 * mm, y, width - 2 * mm, y)
        pdf.setDash()
        y -= 4 * mm

        # — Datos de la venta —
        pdf.setFont("Helvetica", 6)
        for txt in (
            f"Fecha: {venta.fecha:%d/%m/%Y %H:%M}",
            f"Factura: {venta.numero_factura}",
            f"Cliente: {venta.cliente or 'Consumidor Final'}",
        ):
            pdf.drawString(2 * mm, y, txt)
            y -= 6 * mm

        # — Otra línea punteada —
        pdf.setLineWidth(0.3)
        pdf.setDash(1, 2)
        pdf.line(2 * mm, y, width - 2 * mm, y)
        pdf.setDash()
        y -= 4 * mm

        # — Encabezado de tabla de productos —
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(2 * mm, y, "Producto")
        pdf.drawRightString(width - 22 * mm, y, "Cant.")
        pdf.drawRightString(width - 12 * mm, y, "Precio")
        pdf.drawRightString(width -  2 * mm, y, "Total")
        y -= 8 * mm
        pdf.line(2 * mm, y, width - 2 * mm, y)
        y -= 4 * mm

        # — Filas de productos —
        pdf.setFont("Courier", 6)
        for d in detalles:
            name = d.producto_talla.producto.nombre[:16]
            pdf.drawString(2 * mm, y, name)
            pdf.drawRightString(width - 22 * mm, y, str(d.cantidad))
            pdf.drawRightString(width - 12 * mm, y, f"${d.precio:,.0f}")
            pdf.drawRightString(width -  2 * mm, y, f"${d.total:,.0f}")
            y -= 7 * mm

        y -= 4 * mm
        pdf.line(2 * mm, y, width - 2 * mm, y)
        y -= 8 * mm

        # — Recuadro y resaltado del TOTAL —
        pdf.setLineWidth(0.5)
        pdf.rect(2 * mm, y - 12, width - 4 * mm, 14, fill=0, stroke=1)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(4 * mm, y, "TOTAL A PAGAR:")
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(width - 4 * mm, y, f"${venta.total:,.0f}")
        y -= 18 * mm

        # — Método de pago —
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(2 * mm, y, "Método Pago:")
        pdf.drawRightString(width - 4 * mm, y, venta.get_metodo_pago_display())
        y -= 20 * mm

        # — Línea final —
        pdf.setLineWidth(0.3)
        pdf.line(2 * mm, y, width - 2 * mm, y)
        y -= 8 * mm

        # — QR centrado y enmarcado —
        qr_img = ImageReader(qr_buffer)
        qr_size = 25 * mm
        x_qr = (width - qr_size) / 2
        pdf.rect(x_qr - 2 * mm, y - qr_size - 2 * mm,
                 qr_size + 4 * mm, qr_size + 4 * mm,
                 fill=0, stroke=1)
        pdf.drawImage(qr_img, x_qr, y - qr_size, qr_size, qr_size)
        y -= qr_size + 8 * mm

        # — Mensaje final —
        pdf.setFont("Helvetica-Oblique", 6)
        pdf.drawCentredString(width / 2, y, "¡Gracias por tu preferencia!")

        pdf.save()
        buf.seek(0)
        filename = f"factura_{venta.numero_factura}.pdf"
        return FileResponse(buf, as_attachment=True, filename=filename)

    # 2) Si es POST, impresión directa en Windows
    if request.method == "POST":
        if sistema == "Windows":
            try:
                # Reconstruye el contenido de texto
                contenido = f"FACTURA N°: {venta.numero_factura}\n"
                contenido += f"Fecha: {venta.fecha:%d/%m/%Y %H:%M}\n\n"
                for d in detalles:
                    contenido += (
                        f"{d.producto_talla.producto.nombre[:12]:12}"
                        f" {d.cantidad:3} x ${d.precio:7.2f}\n"
                    )
                contenido += f"\nTOTAL: ${venta.total:.2f}\n"
                contenido += f"MÉTODO: {venta.get_metodo_pago_display()}\n"

                import win32print
                printer = win32print.GetDefaultPrinter()
                h = win32print.OpenPrinter(printer)
                win32print.StartDocPrinter(h, 1, ("Factura", None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, contenido.encode("utf-8"))
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
                win32print.ClosePrinter(h)

                return JsonResponse({"success": True})
            except Exception as e:
                return JsonResponse({"success": False, "error": str(e)})
        else:
            return JsonResponse({
                "success": False,
                "error": f"Impresión directa solo en Windows ({sistema})"
            })

    # 3) GET normal: vista previa en pantalla
    return render(request,
                  'dashboard/ventas/imprimir_factura.html',
                  {
                      'venta': venta,
                      'detalles': detalles,
                      'qr_base64': base64.b64encode(qr_buffer.getvalue()).decode('utf-8'),
                      'sistema': sistema,
                  }
    )

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
        ctx = super().get_context_data(**kwargs)
        ctx['detalles'] = self.object.detalles.all()
        return ctx


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

def caja_diaria_view(request):
    hoy = timezone.localdate()
    caja, creada = CajaDiaria.objects.get_or_create(fecha=hoy)
    if request.method == 'POST':
        form = CajaDiariaForm(request.POST, instance=caja)
        if form.is_valid():
            form.save()
            return redirect('ventas:caja_diaria')
    else:
        form = CajaDiariaForm(instance=caja)

    contexto = {
        'form': form,
        'caja': caja,
        'ventas_totales': caja.ventas_totales,
        'neto': caja.neto,
    }
    return render(request, 'ventas/caja_diaria.html', contexto)


@login_required
def ventas_por_dia(request):
    fecha_str = request.GET.get('fecha')
    ayer = request.GET.get('ayer')
    ventas = []
    caja = None
    fecha = None

    if ayer:
        fecha = timezone.now().date() - timedelta(days=1)
        ventas = Venta.objects.filter(fecha__date=fecha).prefetch_related('detalles__producto_talla')
        caja = CajaDiaria.objects.filter(fecha=fecha).first()
    elif fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
            ventas = Venta.objects.filter(fecha__date=fecha).prefetch_related('detalles__producto_talla')
            caja = CajaDiaria.objects.filter(fecha=fecha).first()
        except ValueError:
            pass

    total_ventas = sum(v.total for v in ventas)

    context = {
        'ventas': ventas,
        'fecha': fecha,
        'total_ventas_dia': total_ventas,
        'caja': caja,
    }
    return render(request, 'dashboard/ventas/ventas_por_dia.html', context)

# Métodos de Pago
class MetodoPagoListView(ListView):
    model = MetodoPago
    template_name = 'dashboard/ventas/listado_metodopago.html'
    context_object_name = 'metodos'

class MetodoPagoCreateView(CreateView):
    model = MetodoPago
    form_class = MetodoPagoForm
    template_name = 'dashboard/ventas/metodopago_form.html'
    success_url = reverse_lazy('ventas:metodopago_list')

class MetodoPagoUpdateView(UpdateView):
    model = MetodoPago
    form_class = MetodoPagoForm
    template_name = 'dashboard/ventas/metodopago_form.html'
    success_url = reverse_lazy('ventas:metodopago_list')

class MetodoPagoDeleteView(DeleteView):
    model = MetodoPago
    template_name = 'dashboard/ventas/metodopago_confirm_delete.html'
    success_url = reverse_lazy('ventas:metodopago_list')