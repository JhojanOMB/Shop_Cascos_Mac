from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import DetalleVenta, ProductoTalla

class VentaService:

    @staticmethod
    def crear_venta_con_detalles(usuario, datos_post, form):
        productos_ids  = datos_post.getlist('productos_ids')
        cantidades     = datos_post.getlist('cantidades')
        precios_str    = datos_post.getlist('precios')  # <-- lista de precios enviados

        if not productos_ids or not cantidades:
            raise ValueError("No se pueden crear ventas sin productos.")

        with transaction.atomic():
            venta = form.save(commit=False)
            venta.empleado = usuario
            venta.fecha    = timezone.now()
            venta.total    = 0
            venta.save()

            total_venta = Decimal('0.00')

            for idx, (producto_id, cantidad_str) in enumerate(zip(productos_ids, cantidades)):
                producto_talla = ProductoTalla.objects.get(id=producto_id)
                cantidad       = int(cantidad_str)

                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor a cero.")

                if producto_talla.cantidad < cantidad:
                    raise ValueError(
                        f"No hay suficiente inventario para {producto_talla.producto.nombre} talla "
                        f"{producto_talla.talla.nombre}."
                    )

                # Determinar el precio: si llega un precio válido en precios_str lo usamos,
                # si no, usamos el precio por defecto en producto_talla.producto.precio_venta
                precio = producto_talla.producto.precio_venta
                try:
                    precio_input = precios_str[idx].strip()
                    if precio_input:
                        precio = Decimal(precio_input)
                except (IndexError, Decimal.InvalidOperation):
                    # en caso de error de índice o conversión, ignoramos y quedamos con el precio por defecto
                    pass

                detalle = DetalleVenta(
                    venta=venta,
                    producto_talla=producto_talla,
                    cantidad=cantidad,
                    precio=precio
                )
                detalle.calcular_total()  # total = cantidad * precio
                detalle.save()

                # descontar inventario
                producto_talla.cantidad -= cantidad
                producto_talla.save()

                total_venta += detalle.total

            if total_venta <= 0:
                venta.delete()
                raise ValueError("El total de la venta no puede ser menor o igual a $0.")

            venta.total = total_venta
            venta.save(update_fields=['total'])
            return venta
