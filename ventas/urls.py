
# tienda/urls.py
from django.urls import path
from . import views
from .views import *

app_name = 'ventas'

urlpatterns = [
    # Gestión de ventas
    path('venta/', views.VentaContenidoView.as_view(), name='contenido_ventas'),
    path('venta/crear/', views.VentaCreateView.as_view(), name='crear_venta'),
    path('venta/<int:pk>/edit/', views.VentaUpdateView.as_view(), name='editar_venta'),
    path('venta/<int:pk>/delete/', views.VentaDeleteView.as_view(), name='eliminar_venta'),
    path('obtener-producto/', views.obtener_producto_por_codigo, name='obtener_producto_por_codigo'),
    path('factura/<int:venta_id>/', imprimir_factura, name='imprimir_factura'),
    path('ver-factura/<str:numero_factura>/', PublicVentaDetalleView.as_view(), name='ver_factura'),
    path('ver-factura-restringida/<str:numero_factura>/', VentaDetalleView.as_view(), name='ver_factura_restringida'),
    path('detalle/anular/<int:detalle_id>/', views.anular_detalle_venta, name='anular_detalle'),

]