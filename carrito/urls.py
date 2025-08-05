# carrito/urls.py
from django.urls import path
from . import views

app_name = 'carrito'

urlpatterns = [
    path('', views.ver_carrito, name='ver_carrito'),
    path('agregar/<int:producto_talla_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('update/<int:producto_talla_id>/', views.actualizar_cantidad, name='actualizar_cantidad'),
    path('remove/<int:producto_talla_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('vaciar/', views.vaciar_carrito, name='vaciar_carrito'),            # <- añade esta línea
    path('checkout-whatsapp/', views.enviar_carrito, name='enviar_carrito'),
]
