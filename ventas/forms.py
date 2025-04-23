# tienda/forms.py
from django import forms
from .models import *
from datetime import datetime
from django.forms import modelformset_factory
from django.utils import timezone

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['empleado', 'metodo_pago']

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        user = initial.get('empleado')
        super().__init__(*args, **kwargs)
        if user:
            self.fields['empleado'].initial = user
        self.fields['empleado'].disabled = True  # Protección contra edición

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.fecha = timezone.now()
        instance.save()
        return instance


class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['producto_talla', 'cantidad']

    def clean_producto_talla(self):
        producto_talla = self.cleaned_data.get('producto_talla')
        if not producto_talla:
            raise forms.ValidationError('Este campo es obligatorio.')
        return producto_talla

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        producto_talla = self.cleaned_data.get('producto_talla')

        if producto_talla and producto_talla.cantidad < cantidad:
            raise forms.ValidationError('No hay suficiente inventario para esta talla del producto.')
        return cantidad

# FormSet para manejar múltiples DetalleVenta
DetalleVentaFormSet = modelformset_factory(
    DetalleVenta,
    form=DetalleVentaForm,
    extra=1 
)