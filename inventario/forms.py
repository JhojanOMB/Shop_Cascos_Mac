from django import forms
from .models import Inventario
from tienda.models import *
from django.core.exceptions import ValidationError

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['producto', 'cantidad']

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        producto_talla = self.cleaned_data.get('producto')  # Asegurarse de que es ProductoTalla

        # Verificar la cantidad total disponible
        total_cantidad = producto_talla.producto.calcular_total_cantidad()

        if cantidad < 0:
            raise ValidationError("La cantidad no puede ser negativa.")
        
        if cantidad > total_cantidad:
            raise ValidationError(f"No hay suficiente inventario para el producto {producto_talla.producto.nombre}. "
                                  f"Inventario disponible: {total_cantidad}, solicitado: {cantidad}.")
        return cantidad
