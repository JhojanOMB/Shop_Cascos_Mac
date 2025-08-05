# facturacion/forms.py

from django import forms
from .models import ConfiguracionFacturaElectronica

class ConfiguracionFacturaElectronicaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionFacturaElectronica
        fields = [
            'nit', 'razon_social', 'certificado', 'contrasena_certificado',
            'software_id', 'pin', 'modo', 'habilitado'
        ]
        widgets = {
            'nit': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 placeholder:text-sm',
                'placeholder': 'Ejemplo: 900123456'
            }),
            'razon_social': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 placeholder:text-sm',
                'placeholder': 'Tu razón social registrada'
            }),
            'certificado': forms.ClearableFileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-600 file:bg-blue-50 file:border file:border-gray-300 file:rounded-md file:px-3 file:py-2 file:text-blue-700 file:cursor-pointer hover:file:bg-blue-100 placeholder:text-sm',
                'accept': '.p12'
            }),
            'contrasena_certificado': forms.PasswordInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 placeholder:text-sm',
                'placeholder': 'Contraseña del .p12'
            }),
            'software_id': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 placeholder:text-sm',
                'placeholder': 'ID de software asignado por DIAN'
            }),
            'pin': forms.PasswordInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500 placeholder:text-sm',
                'placeholder': 'PIN de tu software'
            }),
            'modo': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-blue-500 focus:border-blue-500'
            }),
            'habilitado': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
        }
        help_texts = {
            'nit': 'Número de identificación tributaria (NIT) del emisor.',
            'razon_social': 'Nombre o razón social registrada ante la DIAN.',
            'certificado': 'Sube el archivo .p12 que contiene tu certificado digital.',
            'contrasena_certificado': 'Contraseña que protege tu archivo .p12.',
            'software_id': 'Identificador de tu software ante la DIAN.',
            'pin': 'PIN proporcionado al registrar tu software.',
            'modo': 'Pruebas o Producción según tu entorno.',
            'habilitado': 'Marca para activar o desactivar esta configuración.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default_class = (
            'mt-1 block w-full rounded-md border-gray-300 shadow-sm '
            'focus:ring-blue-500 focus:border-blue-500 placeholder:text-sm'
        )
        for name, field in self.fields.items():
            if name not in self.Meta.widgets:
                field.widget.attrs.update({'class': default_class})

    def clean_certificado(self):
        certificado = self.cleaned_data.get('certificado')
        if certificado and not certificado.name.lower().endswith('.p12'):
            raise forms.ValidationError('Solo se permiten archivos con extensión .p12')
        return certificado
