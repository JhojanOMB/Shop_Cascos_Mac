from django import forms
from .models import *
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

class ActualizarCantidadForm(forms.ModelForm):
    class Meta:
        model = ProductoTalla
        fields = ['cantidad']

class MovimientoInventarioForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = ['producto_talla', 'motivo', 'cantidad', 'comentario']
        widgets = {
            'producto_talla': forms.Select(attrs={'class': 'form-select select2'}),
        }

    def __init__(self, *args, **kwargs):
        # Capturamos producto_talla_id si se envía explícitamente
        producto_talla_id = kwargs.pop('producto_talla_id', None)
        super().__init__(*args, **kwargs)
        if producto_talla_id or self.initial.get('producto_talla'):
            # Si se pasa un producto_talla, ocultamos el campo para que no se modifique
            self.fields['producto_talla'].widget = forms.HiddenInput()