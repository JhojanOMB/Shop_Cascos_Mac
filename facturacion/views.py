# facturacion/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ventas.models import Venta
from .models import ConfiguracionFacturaElectronica
from .forms import ConfiguracionFacturaElectronicaForm

@login_required
def configurar_facturacion(request):
    """
    Permite al usuario configurar sus datos de facturación electrónica.
    """
    # Cargar (o crear) la configuración para este usuario
    try:
        configuracion = ConfiguracionFacturaElectronica.objects.get(usuario=request.user)
    except ConfiguracionFacturaElectronica.DoesNotExist:
        configuracion = None

    if request.method == "POST":
        form = ConfiguracionFacturaElectronicaForm(
            request.POST, request.FILES, instance=configuracion
        )
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.usuario = request.user
            nueva.save()
            messages.success(request, "Configuración guardada correctamente.")
            # Redirige usando el namespace de la app
            return redirect('facturacion:configurar_facturacion')
        else:
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = ConfiguracionFacturaElectronicaForm(instance=configuracion)

    return render(request,
                  "dashboard/facturacion/configurar_facturacion.html",
                  {
                      'form': form,
                      'configuracion': configuracion,
                  }
    )

@login_required
def generar_factura_electronica(request, venta_numero):
    """
    Llama al servicio externo y marca la venta como facturada electrónicamente.
    """
    venta = get_object_or_404(Venta, numero_factura=venta_numero)

    # Aquí iría la llamada real a la DIAN / Facho…
    exito = True  # simulado

    if exito:
        # Asegúrate de que tu modelo Venta tenga el campo booleano `facturada_electronicamente`
        venta.facturada_electronicamente = True
        venta.save()
        messages.success(request, "Factura electrónica generada correctamente.")
    else:
        messages.error(request, "Error al generar la factura electrónica.")

    # Redirige al detalle de la venta (namespace 'ventas')
    return redirect('ventas:detalle_venta', numero_factura=venta.numero_factura)
