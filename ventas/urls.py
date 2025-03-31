
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
    path('agregar-producto/', views.agregar_producto_a_venta, name='agregar_producto_a_venta'),
    path('factura/<int:venta_id>/', imprimir_factura, name='imprimir_factura'),
    path('consultar-factura/<str:numero_factura>/', views.consulta_factura, name='consulta_factura'),
    path('ver-factura/<int:pk>/', views.ver_factura, name='ver_factura'),
    path('ver-factura-restringida/<str:numero_factura>/', views.ver_factura_restringida, name='ver_factura_restringida'),
]