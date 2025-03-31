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
    form_class = VentaForm  # Usamos el formulario personalizado
    template_name = 'dashboard/ventas/crear_venta.html'
    success_url = reverse_lazy('ventas:contenido_ventas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metodos_pago'] = METODOS_PAGO  # Agregar métodos de pago al contexto
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasamos el usuario autenticado como inicial para el formulario
        kwargs.update({'initial': {'empleado': self.request.user}})
        return kwargs

    def form_valid(self, form):
        venta = form.save(commit=False)
        venta.empleado = self.request.user
        venta.fecha = timezone.now()
        venta.total = 0

        productos_ids = self.request.POST.getlist('productos_ids')
        cantidades = self.request.POST.getlist('cantidades')

        # Validamos que existan productos y cantidades
        if not productos_ids or not cantidades:
            messages.error(self.request, "No se pueden crear ventas sin productos.")
            return self.form_invalid(form)

        with transaction.atomic():
            total = 0
            for producto_id, cantidad_str in zip(productos_ids, cantidades):
                try:
                    producto_talla = ProductoTalla.objects.get(id=producto_id)
                    cantidad = int(cantidad_str)

                    # Validar inventario
                    if producto_talla.cantidad < cantidad:
                        messages.error(self.request, f"No hay suficiente inventario para {producto_talla.producto.nombre} en talla {producto_talla.talla.nombre}.")
                        return self.form_invalid(form)

                    # Crear el detalle de venta
                    detalle = DetalleVenta(
                        venta=venta,
                        producto_talla=producto_talla,
                        cantidad=cantidad,
                        precio=producto_talla.producto.precio
                    )
                    detalle.calcular_total()
                    detalle.save()

                    # Acumular total de la venta
                    total += detalle.total
                except ProductoTalla.DoesNotExist:
                    messages.error(self.request, f"El producto con ID {producto_id} no existe.")
                    return self.form_invalid(form)
                except ValueError:
                    messages.error(self.request, "La cantidad debe ser un número válido.")
                    return self.form_invalid(form)
                except ValidationError as e:
                    messages.error(self.request, str(e))
                    return self.form_invalid(form)

            # Guardar el total y finalizar la venta
            venta.total = total
            venta.save()

            messages.success(self.request, f"Venta realizada con éxito. Total: {venta.total}")

            # Redirigir a la vista de impresión de factura
            return redirect('ventas:imprimir_factura', venta_id=venta.id)

        return super().form_valid(form)

def obtener_producto_por_codigo(request):
    codigo_barras = request.GET.get('codigo_barras')
    if not codigo_barras:
        return JsonResponse({
            'success': False,
            'message': 'Debe proporcionar un código de barras.'
        }, status=400)

    # Crear una consulta que busque tanto con como sin el primer cero
    try:
        producto_talla = ProductoTalla.objects.select_related('producto', 'talla').get(
            Q(codigo_barras=codigo_barras) | Q(codigo_barras='0' + codigo_barras)
        )

        data = {
            'success': True,
            'producto': {
                'id': producto_talla.id,
                'nombre': producto_talla.producto.nombre,
                'precio': float(producto_talla.producto.precio),
                'stock': producto_talla.cantidad,
                'talla': producto_talla.talla.nombre,
            }
        }
    except ProductoTalla.DoesNotExist:
        data = {
            'success': False,
            'message': 'Producto no encontrado o código de barras incorrecto.',
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
def agregar_producto_a_venta(request):
    venta_id = request.POST.get('venta_id')
    codigo_barras = request.POST.get('codigo_barras')
    cantidad = int(request.POST.get('cantidad', 1))

    try:
        # Obtener la venta
        venta = Venta.objects.get(id=venta_id)
        # Obtener el producto correspondiente al código de barras
        producto_talla = ProductoTalla.objects.get(codigo_barras=codigo_barras)

        if producto_talla.cantidad < cantidad:
            return JsonResponse({'success': False, 'message': f'No hay suficiente stock para {producto_talla.producto.nombre} en talla {producto_talla.talla.nombre}.'}, status=400)

        # Crear o actualizar el DetalleVenta
        detalle, created = DetalleVenta.objects.get_or_create(
            venta=venta,
            producto_talla=producto_talla,
            defaults={'cantidad': cantidad, 'precio': producto_talla.producto.precio}
        )

        if not created:
            # Si el detalle ya existía, actualizamos la cantidad y el total
            detalle.cantidad += cantidad  # Este aumento puede ser la causa del problema
            detalle.calcular_total()
        else:
            # Si es nuevo, se calcula el total y se descuenta inventario
            detalle.calcular_total()

        # Descontar inventario
        detalle.descontar_inventario()
        detalle.save()

        # Actualizar el total de la venta
        venta.calcular_total()

        return JsonResponse({
            'success': True,
            'message': 'Producto agregado a la venta',
            'detalle_total': detalle.total,
            'venta_total': venta.total
        })

    except ProductoTalla.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


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
    # Obtenemos la venta y sus detalles
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)

    # Generar contenido de la factura para la impresión directa
    contenido = f"""
    FACTURA N°: {venta.id}
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

    # Generar Código QR
    qr = qrcode.make(f"http://127.0.0.1:8000/ventas/factura/{venta.id}/")
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')

    # Si es POST, intentar enviar a la impresora
    if request.method == "POST":
        if platform.system() == "Windows" and win32print:
            try:
                printer_name = win32print.GetDefaultPrinter()
                hprinter = win32print.OpenPrinter(printer_name)
                win32print.StartDocPrinter(hprinter, 1, ("Factura", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, contenido.encode('utf-8'))
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
                win32print.ClosePrinter(hprinter)
                return HttpResponse("Factura enviada a la impresora correctamente.")
            except Exception as e:
                return HttpResponse(f"Error al imprimir: {str(e)}")
        else:
            return HttpResponse("La impresión directa solo está disponible en Windows.")

    # Si es GET, renderizar la factura para vista previa
    return render(request, 'dashboard/ventas/imprimir_factura.html', {
        'venta': venta,
        'detalles': detalles,
        'qr_base64': qr_base64
    })


def consulta_factura(request, numero_factura):
    venta = get_object_or_404(Venta, numero_factura=numero_factura)
    return render(request, 'dashboard/ventas/detalle_venta.html', {'venta': venta})

def ver_factura_restringida(request, numero_factura):
    venta = get_object_or_404(Venta, numero_factura=numero_factura)
    if not request.user.is_authenticated:
        return HttpResponseForbidden("No tienes permiso para acceder a esta factura.")
    return render(request, 'dashboard/ventas/detalle_venta.html', {'venta': venta})

def ver_factura(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    return render(request, 'dashboard/ventas/detalle_venta.html', {'venta': venta})
