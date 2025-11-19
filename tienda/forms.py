# tienda/forms.py
from django import forms
from .models import *
from datetime import datetime
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError

ICON_MAP = {
    'nombre': 'bi bi-shop-window',
    'descripcion': 'bi bi-journal-text',
    'referencia': 'bi bi-key',
    'precio': 'bi bi-cash-stack',    # engloba precio_venta, precio_compra, precio_oferta
    'categoria': 'bi bi-list',
    'imagen': 'bi bi-image',
    'catalogo': 'bi bi-book',
    'proveedor': 'bi bi-people',
    'marca': 'bi bi-box-seam',
    'en_oferta': 'bi bi-tag',
    'talla': 'bi bi-rulers',
    'cantidad': 'bi bi-box-seam',
    'color': 'bi bi-droplet',
    'genero': 'bi bi-gender-ambiguous',
    'telefono': 'bi bi-telephone',
    'correo': 'bi bi-envelope',
}

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'referencia', 'precio_venta', 'precio_compra', 'categoria',
            'imagen1', 'imagen2', 'imagen3', 'imagen4', 'imagen5', 'catalogo',
            'proveedor', 'en_oferta', 'precio_oferta', 'marca'
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'en_oferta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'marca': forms.Select(attrs={'class': 'form-control'}),
            # Los campos de precio se sobrescribirán en __init__ a TextInput para permitir formato personalizado
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- convertir campos de precio a TextInput para facilitar la entrada (ej: "12,000.50")
        precio_fields = ['precio_venta', 'precio_compra', 'precio_oferta']
        for field_name in precio_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.TextInput(attrs={
                    'class': 'form-control precio-input',
                    'placeholder': '0.00'
                })

        # --- clases por defecto y atributos específicos por campo (si existen)
        field_defaults = {
            'nombre': {'class': 'form-control', 'autofocus': True},
            'descripcion': {'class': 'form-control', 'rows': 3},
            'referencia': {'class': 'form-control'},
            'imagen1': {'class': 'form-control'},
            'imagen2': {'class': 'form-control'},
            'imagen3': {'class': 'form-control'},
            'imagen4': {'class': 'form-control'},
            'imagen5': {'class': 'form-control'},
            'catalogo': {'class': 'form-control'},
            'proveedor': {'class': 'form-control'},
            'marca': {'class': 'form-control'},
        }

        for nombre_campo, campo in self.fields.items():
            # añade clases por defecto si no existen
            attrs = campo.widget.attrs
            # si no tiene clase, asegúrate de añadirla
            if 'class' not in attrs:
                attrs['class'] = 'form-control'
            # mezcla con valores específicos definidos arriba
            if nombre_campo in field_defaults:
                for k, v in field_defaults[nombre_campo].items():
                    # concatena clases si se especifica 'class'
                    if k == 'class':
                        if 'class' in attrs:
                            attrs['class'] = f"{attrs['class']} {v}"
                        else:
                            attrs['class'] = v
                    else:
                        attrs[k] = v

            # --- asignar icono automáticamente basado en el nombre del campo
            lower = nombre_campo.lower()
            icono = None
            for clave, clase in ICON_MAP.items():
                if clave in lower:
                    icono = clase
                    break
            if not icono:
                icono = 'bi bi-question-circle'  # fallback
            attrs['icon'] = icono

            # marca los inputs de precio con placeholder si es uno de ellos
            if nombre_campo in precio_fields:
                attrs.setdefault('placeholder', '0.00')
                attrs.setdefault('inputmode', 'decimal')

    # --- parseo seguro de precios (Decimal)
    def _parse_price(self, field_name):
        valor = self.cleaned_data.get(field_name)
        if valor in (None, ''):
            return None
        # Aceptar entrada con comas o espacios: "12,345.67" o "12.345,67"
        texto = str(valor).strip()
        # Normalizar: quitar espacios y comas de miles
        texto = texto.replace(' ', '')
        # Si el usuario usa coma como separador decimal (ej: "1234,56"), convertirla
        # Detectamos si hay más de una coma o punto para evitar errores extraños:
        # Si hay tanto coma como punto y la coma aparece después del punto -> asumimos formato "1.234,56"
        if ',' in texto and '.' in texto:
            if texto.rfind(',') > texto.rfind('.'):
                texto = texto.replace('.', '').replace(',', '.')
            else:
                texto = texto.replace(',', '')
        else:
            # si solo hay comas, las consideramos separador decimal
            if ',' in texto and '.' not in texto:
                texto = texto.replace(',', '.')
            else:
                texto = texto.replace(',', '')

        try:
            return Decimal(texto)
        except (InvalidOperation, ValueError):
            raise ValidationError(f"El valor de {field_name} debe ser un número válido.")

    # nombre correcto para que Django lo ejecute en el campo precio_venta
    def clean_precio_venta(self):
        return self._parse_price('precio_venta')

    def clean_precio_compra(self):
        return self._parse_price('precio_compra')

    def clean_precio_oferta(self):
        return self._parse_price('precio_oferta')

    def clean(self):
        cleaned_data = super().clean()
        en_oferta = cleaned_data.get('en_oferta')
        precio_venta = cleaned_data.get('precio_venta')
        precio_oferta = cleaned_data.get('precio_oferta')

        # Validar que el precio de oferta sea menor que el precio normal si está en oferta
        if en_oferta:
            # Solo validar si se suministro precio_oferta
            if precio_oferta is not None:
                if precio_venta is None or precio_oferta >= precio_venta:
                    self.add_error('precio_oferta', 'El precio de oferta debe ser menor que el precio normal.')
            else:
                # si está en oferta pero no hay precio de oferta, marcarlo como error
                self.add_error('precio_oferta', 'Debe ingresar un precio de oferta si marca "en oferta".')

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


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la marca',
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        return nombre.title() if nombre else nombre

    def __init__(self, *args, **kwargs):
        super(MarcaForm, self).__init__(*args, **kwargs)
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
