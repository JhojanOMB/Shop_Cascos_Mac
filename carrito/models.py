# carrito/models.py
from django.conf import settings
from django.db import models
from tienda.models import *

# Modelo de Carrito de Compras
class Carrito(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, related_name='items', on_delete=models.CASCADE)
    producto_talla = models.ForeignKey(ProductoTalla, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)  # Añadir un valor predeterminado

    def __str__(self):
        return f"{self.cantidad} x {self.producto_talla.producto.nombre} ({self.producto_talla.talla.nombre})"
