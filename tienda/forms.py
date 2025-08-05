# tienda/forms.py
from django import forms
from .models import *
from datetime import datetime
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

class ProductoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Convertir los campos de precio a texto
        precio_fields = ['precio_venta', 'precio_compra', 'precio_oferta']
        for field in precio_fields:
            self.fields[field].widget = forms.TextInput(attrs={'class': 'form-control precio-input'})

        # Aplicar clases CSS a otros campos
        self.fields['nombre'].widget.attrs.update({'class': 'form-control', 'autofocus': True})
        self.fields['descripcion'].widget.attrs.update({'class': 'form-control'})
        self.fields['categoria'].widget.attrs.update({'class': 'form-control'})
        self.fields['imagen1'].widget.attrs.update({'class': 'form-control'})
        self.fields['imagen2'].widget.attrs.update({'class': 'form-control'})
        self.fields['imagen3'].widget.attrs.update({'class': 'form-control'})
        self.fields['imagen4'].widget.attrs.update({'class': 'form-control'})
        self.fields['imagen5'].widget.attrs.update({'class': 'form-control'})
        self.fields['proveedor'].widget.attrs.update({'class': 'form-control'})
        

    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'referencia', 'precio_venta', 'precio_compra', 'categoria', 
            'imagen1', 'imagen2', 'imagen3', 'imagen4', 'imagen5', 'catalogo',
            'proveedor', 'en_oferta', 'precio_oferta'
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'en_oferta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_precio(self):
        return self._parse_price('precio_venta')

    def clean_precio_compra(self):
        return self._parse_price('precio_compra')

    def clean_precio_oferta(self):
        return self._parse_price('precio_oferta')

    def _parse_price(self, field_name):
        """ Convierte el precio ingresado a Decimal, eliminando comas y espacios """
        valor = self.cleaned_data.get(field_name)

        if valor in [None, '']:  # Si el valor es nulo o vacío, regresamos None
            return None
        
        try:
            valor = str(valor).replace(',', '').strip()  # Eliminar comas y espacios
            return Decimal(valor)
        except:
            raise ValidationError(f"El valor de {field_name} debe ser un número válido.")

    def clean(self):
        cleaned_data = super().clean()
        en_oferta = cleaned_data.get('en_oferta')
        precio_venta = cleaned_data.get('precio_venta')
        precio_oferta = cleaned_data.get('precio_oferta')

        # Validar que el precio de oferta sea menor que el precio normal si está en oferta
        if en_oferta and precio_oferta is not None:
            if precio_venta is None or precio_oferta >= precio_venta:
                self.add_error('precio_oferta', 'El precio de oferta debe ser menor que el precio normal.')

        return cleaned_data
    
class ProductoTallaForm(forms.ModelForm):
    class Meta:
        model = ProductoTalla
        fields = ['talla', 'cantidad', 'color', 'genero']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asigna la clase CSS para que se muestre bien en Bootstrap
        for field in ['talla', 'cantidad', 'color', 'genero']:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        talla = cleaned_data.get('talla')
        cantidad = cleaned_data.get('cantidad')
        color = cleaned_data.get('color')
        genero = cleaned_data.get('genero')

        # Si se ha llenado alguno de estos campos, se exigen todos
        if talla or cantidad or color or genero:
            missing_fields = []
            if not talla:
                missing_fields.append("Talla")
            # Nota: para cantidad verificamos si es None o vacío
            if cantidad in (None, ''):
                missing_fields.append("Cantidad")
            if not color:
                missing_fields.append("Color")
            if not genero:
                missing_fields.append("Género")
            if missing_fields:
                raise forms.ValidationError("Debe completar los siguientes campos: " + ", ".join(missing_fields))
        return cleaned_data

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'direccion', 'telefono', 'correo_electronico', 'provedor_de']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del proveedor',
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección del proveedor',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono',
            }),
            'correo_electronico': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Correo electrónico',
            }),
            'provedor_de': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '¿Proveedor de qué?',
            }),
        }
        labels = {
            'nombre': 'Nombre',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'correo_electronico': 'Correo electrónico',
            'provedor_de': 'Proveedor de',
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        return nombre.title() if nombre else nombre

    def clean_direccion(self):
        direccion = self.cleaned_data.get('direccion')
        return direccion.title() if direccion else direccion

    def clean_provedor_de(self):
        provedor_de = self.cleaned_data.get('provedor_de')
        return provedor_de.title() if provedor_de else provedor_de

    def __init__(self, *args, **kwargs):
        super(ProveedorForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] += ' shadow-sm rounded-3'

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la categoría',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la categoría',
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        return nombre.title() if nombre else nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion')
        return descripcion.capitalize() if descripcion else descripcion

    def __init__(self, *args, **kwargs):
        super(CategoriaForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] += ' shadow-sm rounded-3'

class TallaForm(forms.ModelForm):
    class Meta:
        model = Talla
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        return nombre.upper()

class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['nombre', 'codigo_hex']
        widgets = {
            'codigo_hex': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        return nombre.title()
