from django.db import transaction
from django.utils import timezone
from .models import DetalleVenta, ProductoTalla


class VentaService:

    @staticmethod
    def crear_venta_con_detalles(usuario, datos_post, form):
        productos_ids = datos_post.getlist('productos_ids')
        cantidades = datos_post.getlist('cantidades')

        if not productos_ids or not cantidades:
            raise ValueError("No se pueden crear ventas sin productos.")

        with transaction.atomic():
            venta = form.save(commit=False)
            venta.empleado = usuario
            venta.fecha = timezone.now()
            venta.total = 0
            venta.save()

            total_venta = 0

            for producto_id, cantidad_str in zip(productos_ids, cantidades):
                producto_talla = ProductoTalla.objects.get(id=producto_id)
                cantidad = int(cantidad_str)

                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor a cero.")

                if producto_talla.cantidad < cantidad:
                    raise ValueError(
                        f"No hay suficiente inventario para el producto {producto_talla.producto.nombre} - Talla {producto_talla.talla.nombre}."
                    )

                detalle = DetalleVenta(
                    venta=venta,
                    producto_talla=producto_talla,
                    cantidad=cantidad,
                    precio=producto_talla.producto.precio_venta
                )
                detalle.calcular_total()
                detalle.save()

                producto_talla.cantidad -= cantidad
                producto_talla.save()

                total_venta += detalle.total

            if total_venta <= 0:
                venta.delete()
                raise ValueError("El total de la venta no puede ser menor o igual a $0.")

            venta.total = total_venta
            venta.save()
            return venta
