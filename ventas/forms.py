# tienda/forms.py
from django import forms
from .models import *
from datetime import datetime
from django.forms import modelformset_factory
from django.utils import timezone

class CajaDiariaForm(forms.ModelForm):
    class Meta:
        model = CajaDiaria
        fields = ['apertura', 'gastos']
        labels = {
            'apertura': 'Saldo de apertura',
            'gastos': 'Total de gastos',
        }
        widgets = {
            'apertura': forms.TextInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Ej. 100000.00'
            }),
            'gastos': forms.TextInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Ej. 25000.00'
            }),
        }

    def clean_apertura(self):
        apertura = self.cleaned_data.get('apertura')
        if apertura is None or apertura < 0:
            raise forms.ValidationError("El saldo de apertura debe ser un número ≥ 0.")
        return apertura

    def clean_gastos(self):
        gastos = self.cleaned_data.get('gastos')
        if gastos is None or gastos < 0:
            raise forms.ValidationError("El total de gastos debe ser un número ≥ 0.")
        return gastos


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
        # incluimos 'precio' para que el usuario pueda editarlo
        fields = ['producto_talla', 'cantidad', 'precio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # placeholder con el precio por defecto
        if self.instance and self.instance.producto_talla:
            self.fields['precio'].initial = self.instance.producto_talla.precio
        self.fields['precio'].widget.attrs.update({
            'step': '0.01', 'min': '0'
        })

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        # Si el usuario lo deja en blanco o 0, devolvemos None para interceptarlo luego
        return precio or None

    def clean_producto_talla(self):
        producto_talla = self.cleaned_data.get('producto_talla')
        if not producto_talla:
            raise forms.ValidationError('Este campo es obligatorio.')
        return producto_talla

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        producto_talla = self.cleaned_data.get('producto_talla')
        if producto_talla and cantidad and producto_talla.cantidad < cantidad:
            raise forms.ValidationError('No hay suficiente inventario.')
        return cantidad

# FormSet para manejar múltiples DetalleVenta
DetalleVentaFormSet = modelformset_factory(
    DetalleVenta,
    form=DetalleVentaForm,
    extra=1 
)

class MetodoPagoForm(forms.ModelForm):
    class Meta:
        model = MetodoPago
        fields = ['nombre', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }