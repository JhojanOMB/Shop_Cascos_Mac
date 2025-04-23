# inventario/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('', inventario_view, name='inventario'),
    path('movimiento/', movimiento_inventario_view, name='movimiento_inventario'),
]
