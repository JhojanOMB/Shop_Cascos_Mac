# inventario/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps  # Importa apps
from tienda.models import *

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
