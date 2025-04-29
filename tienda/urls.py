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
    path('codigo-barras/talla/<int:talla_id>/', views.generar_codigo_barras_talla, name='codigo_barras_talla'),
    path('actualizar-todos-codigos-barras/', views.actualizar_todos_codigos_barras, name='actualizar_todos_codigos_barras'),

    # Gestión de productos
    path('producto/', views.ProductoContenidoView.as_view(), name='contenido_productos'),
    path('producto/crear/', views.ProductoCreateView.as_view(), name='crear_producto'),
    path('producto/<int:pk>/edit/', views.ProductoUpdateView.as_view(), name='editar_producto'),
    path('producto/<int:pk>/delete/', views.ProductoDeleteView.as_view(), name='eliminar_producto'),
    path('producto/<slug:slug>/', views.ProductDetailShopView.as_view(), name='detalles_producto_tienda'),
    path('producto/<int:pk>/ver/', views.ProductDetailView.as_view(), name='detalles_producto'),
    path('productos_vendidos_hoy/', views.productos_vendidos_hoy, name='productos_vendidos_hoy'),
    path('buscar/', buscar_productos, name='buscar_productos'),
    path('barcode/<str:codigo_barras>/', generar_codigo_barras, name='barcode_image'),
    path('barcode/talla/<int:producto_talla_id>/', generar_codigo_barras_talla, name='barcode_image_talla'),
    path('imprimir-codigos-barras/', imprimir_codigos_barras, name='imprimir_codigos_barras'),
    path('producto/eliminar-multiples/', eliminar_productos_seleccionados, name='eliminar_productos_seleccionados'),


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

    # Tallas (vistas individuales)
    path('tallas/', TallaListView.as_view(), name='listar_tallas'),
    path('tallas/crear/', TallaCreateView.as_view(), name='crear_talla'),
    path('tallas/editar/<int:pk>/', TallaUpdateView.as_view(), name='editar_talla'),
    path('tallas/eliminar/<int:pk>/', TallaDeleteView.as_view(), name='eliminar_talla'),

    # Colores (vistas individuales)
    path('colores/', ColorListView.as_view(), name='listar_colores'),
    path('colores/crear/', ColorCreateView.as_view(), name='crear_color'),
    path('colores/editar/<int:pk>/', ColorUpdateView.as_view(), name='editar_color'),
    path('colores/eliminar/<int:pk>/', ColorDeleteView.as_view(), name='eliminar_color'),

    # Vista adicionales unificada contiene Tallas y Colores en el dashboard
    path('dashboard/adicionales/', views.AdicionalesListView.as_view(), name='contenido_adicionales'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
