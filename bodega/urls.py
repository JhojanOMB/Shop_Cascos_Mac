from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.contenido_bodegas, name='contenido_bodegas'),  
    path('crear/', views.crear_bodega, name='crear_bodega'),
    path('<int:pk>/', views.detalle_bodega, name='detalle_bodega'),
    path('<int:pk>/editar/', views.editar_bodega, name='editar_bodega'),
    path('transferir/', views.transferir_stock, name='transferir_stock'),
]
