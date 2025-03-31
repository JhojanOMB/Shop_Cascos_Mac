from django.urls import path
from . import views

app_name = 'carrito'

urlpatterns = [
    path('agregar/<int:producto_talla_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('ver/', views.ver_carrito, name='ver_carrito'),
    path('enviar/', views.enviar_carrito, name='enviar_carrito'),
    path('actualizar/<int:producto_talla_id>/', views.actualizar_cantidad, name='actualizar_cantidad'),
    path('eliminar/<int:producto_talla_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
]
