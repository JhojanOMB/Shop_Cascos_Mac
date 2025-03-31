# tienda/urls.py
from django.urls import path
from . import views
from .views import *
from django.conf.urls.static import static

urlpatterns = [
    # Página principal y ubicacion
    path('', views.index, name='index'),
    path('ubicanos', views.ubicanos, name='ubicanos'),


    # Dashboard por roles
    path('dashboard/gerente/', views.dashboard_gerente, name='dashboard_gerente'),
    path('dashboard/vendedor/', views.dashboard_vendedor, name='dashboard_vendedor'),

    # Información general
    path('datos/', views.obtener_datos_ventas, name='obtener_datos_ventas'),

    # Gestión códigos de barras
    path('codigo-barras/producto/<int:producto_id>/', views.generar_codigo_barras_producto, name='codigo_barras_producto'),
    path('codigo-barras/talla/<int:talla_id>/', views.generar_codigo_barras_talla, name='codigo_barras_talla'),
    
    # Gestión de productos
    path('producto/', views.ProductoContenidoView.as_view(), name='contenido_productos'),
    path('producto/crear/', views.ProductoCreateView.as_view(), name='crear_producto'),
    path('producto/<int:pk>/edit/', views.ProductoUpdateView.as_view(), name='editar_producto'),
    path('producto/<int:pk>/delete/', views.ProductoDeleteView.as_view(), name='eliminar_producto'),
    path('producto/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('productos_vendidos_hoy/', views.productos_vendidos_hoy, name='productos_vendidos_hoy'),
    path('buscar/', buscar_productos, name='buscar_productos'),
    path('imprimir-codigos-barras/', imprimir_codigos_barras, name='imprimir_codigos_barras'),

    # Gestión de categorías
    path('categoria/', views.CategoriaContenidoView.as_view(), name='contenido_categorias'),
    path('categoria/crear/', views.CategoriaCreateView.as_view(), name='crear_categoria'),
    path('categoria/<int:pk>/edit/', views.CategoriaUpdateView.as_view(), name='editar_categoria'),
    path('categoria/<int:pk>/delete/', views.CategoriaDeleteView.as_view(), name='eliminar_categoria'),

    # Gestión de proveedores
    path('proveedor/', views.ProveedorContenidoView.as_view(), name='contenido_proveedores'),
    path('proveedor/crear/', views.ProveedorCreateView.as_view(), name='crear_proveedor'),
    path('proveedor/<int:pk>/edit/', views.ProveedorUpdateView.as_view(), name='editar_proveedor'),
    path('proveedor/<int:pk>/delete/', views.ProveedorDeleteView.as_view(), name='eliminar_proveedor'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
