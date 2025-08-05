from django import forms
from tienda.models import Producto
from .models import Bodega, StockBodega

class BodegaForm(forms.ModelForm):
    class Meta:
        model = Bodega
        fields = ['nombre', 'direccion']

class TransferenciaForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.all())
    bodega_origen = forms.ModelChoiceField(queryset=Bodega.objects.all(), label='Bodega Origen')
    bodega_destino = forms.ModelChoiceField(queryset=Bodega.objects.all(), label='Bodega Destino')
    cantidad = forms.IntegerField(min_value=1)

    def save(self):
        prod = self.cleaned_data['producto']
        origen = self.cleaned_data['bodega_origen']
        destino = self.cleaned_data['bodega_destino']
        cantidad = self.cleaned_data['cantidad']

        stock_origen, _ = StockBodega.objects.get_or_create(bodega=origen, producto=prod)
        stock_destino, _ = StockBodega.objects.get_or_create(bodega=destino, producto=prod)

        # Ajustar cantidades
        stock_origen.cantidad = max(stock_origen.cantidad - cantidad, 0)
        stock_destino.cantidad += cantidad
        stock_origen.save()
        stock_destino.save()