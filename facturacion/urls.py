# facturacion/urls.py

from django.urls import path
from .views import configurar_facturacion, generar_factura_electronica

app_name = 'facturacion'

urlpatterns = [
    # Pantalla de configuración
    path('configuracion/', configurar_facturacion, name='configurar_facturacion'),

    # Botón “Generar factura electrónica” desde la vista de venta
    path('generar/<str:venta_numero>/', generar_factura_electronica, name='generar_factura_electronica'),
]
