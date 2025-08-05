# inventario/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps  # Importa apps
from tienda.models import *
from django.conf import settings
from django.db import transaction

class Inventario(models.Model):
    producto = models.ForeignKey('tienda.Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()

    def descontar_inventario(self, cantidad):
        if cantidad > self.cantidad:
            raise ValidationError(f"No hay suficiente inventario de {self.producto.nombre}.")
        self.cantidad -= cantidad
        self.save()

    def actualizar_inventario(self):
        """Actualiza la cantidad total en el inventario basado en las cantidades de cada talla"""
        total_cantidad = self.producto.calcular_total_cantidad()
        self.cantidad = total_cantidad
        self.save()

    def __str__(self):
        return f'{self.producto.nombre} - {self.cantidad}'

class MovimientoInventario(models.Model):
    MOVIMIENTO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]
    producto_talla = models.ForeignKey('tienda.ProductoTalla', on_delete=models.CASCADE, related_name='movimientos')
    cantidad = models.IntegerField(
        help_text=(
            "Ingresa la cantidad según el tipo de movimiento:\n"
            "- Ingreso: cantidad a sumar al inventario.\n"
            "- Salida: cantidad a restar del inventario.\n"
            "- Ajuste: nuevo total exacto en inventario."
        )
    )
    motivo = models.CharField(max_length=20, choices=MOVIMIENTO_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    comentario = models.TextField(blank=True, null=True)


    def save(self, *args, **kwargs):
        with transaction.atomic():
            pt = self.producto_talla

            if self.motivo == 'ingreso':
                pt.cantidad += abs(self.cantidad)
            elif self.motivo == 'salida':
                pt.cantidad -= abs(self.cantidad)
                if pt.cantidad < 0:
                    raise ValueError("La cantidad en inventario no puede ser negativa.")
            elif self.motivo == 'ajuste':
                pt.cantidad = self.cantidad

            pt.save()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Movimiento {self.motivo} de {self.cantidad} en {self.producto_talla}"
