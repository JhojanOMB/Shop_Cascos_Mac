from facturacion.models import ConfiguracionFacturaElectronica, FacturaElectronica

import requests
from django.conf import settings

def enviar_a_dian(factura: 'FacturaElectronica'):
    venta = factura.venta

    try:
        config = ConfiguracionFacturaElectronica.objects.get(usuario=venta.empleado)
    except ConfiguracionFacturaElectronica.DoesNotExist:
        factura.estado = "error"
        factura.respuesta_dian = "No se encontró configuración DIAN para el usuario"
        factura.save()
        return

    data = {
        "numero": venta.numero_factura,
        "fecha_emision": venta.fecha.isoformat(),
        "cliente": {
            "nombre": venta.cliente or "Consumidor Final",
            "correo": venta.cliente_email or "correo@ejemplo.com",
            "identificacion": venta.cliente_nit or "222222222",  # si aplica
        },
        "items": [
            {
                "descripcion": d.producto_talla.producto.nombre,
                "cantidad": d.cantidad,
                "precio_unitario": float(d.precio),
                "total": float(d.total)
            }
            for d in venta.detalles.all()
        ],
        "total": float(venta.total),
        "forma_pago": venta.get_metodo_pago_display(),
        # Datos del software cliente:
        "emisor": {
            "nit": config.nit,
            "razon_social": config.razon_social,
            "software_id": config.software_id,
            "pin": config.pin
        }
    }

    headers = {
        "Authorization": f"Bearer {config.token_acceso}",  # si FACHO lo requiere
        "Content-Type": "application/json"
    }

    response = requests.post(settings.FACHO_API_URL, json=data, headers=headers)

    if response.status_code == 200:
        resultado = response.json()
        factura.estado = "enviada"
        factura.numero_cufe = resultado.get("cufe")
        factura.xml = resultado.get("xml")
        factura.respuesta_dian = response.text
    else:
        factura.estado = "rechazada"
        factura.respuesta_dian = response.text

    factura.save()
