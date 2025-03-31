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
        self.fields['genero'].widget.attrs.update({'class': 'form-select'})
        

    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio_venta', 'precio_compra', 'categoria', 
            'imagen1', 'imagen2', 'imagen3', 'imagen4', 'imagen5', 'genero', 'catalogo',
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

        # Validar el género solo si es obligatorio para la categoría
        genero = cleaned_data.get('genero')
        categoria = cleaned_data.get('categoria')

        categorias_requieren_genero = ["Cascos", "Chaquetas"] 

        if categoria and categoria.nombre in categorias_requieren_genero:
            if not genero or genero == 'no_especificado':
                self.add_error('genero', 'Debes seleccionar un género para esta categoría.')

        return cleaned_data
    
class ProductoTallaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['talla'].widget.attrs.update({'class': 'form-control'})
        self.fields['cantidad'].widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = ProductoTalla
        fields = ['talla', 'cantidad']

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor 
        fields = ['nombre', 'direccion', 'telefono', 'correo_electronico', 'provedor_de']

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion'] 

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción de la categoría'}),
        }
