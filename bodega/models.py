from django.db import models
from tienda.models import Producto

class Bodega(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.nombre

class StockBodega(models.Model):
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='stocks')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='stocks_bodega')
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('bodega', 'producto')

    def __str__(self):
        return f"{self.producto.nombre} en {self.bodega.nombre}: {self.cantidad}"