from django.contrib import admin
from django.urls import path, include
from tienda import views as tienda_views
from usuarios import views as usuarios_views
from inventario.views import *
from dashboards.views import *
from carrito.views import *  # Importamos las vistas del carrito de compras
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', usuarios_views.login_page, name='login'),
    path('logout/', usuarios_views.logout_view, name='logout'),
    path('tienda/', include('tienda.urls')),  # Incluye las URLs de la aplicación tienda
    path('ventas/', include('ventas.urls')),  # Incluye las URLs de la aplicación ventas
    path('dashboards/', include('dashboards.urls')),  # Incluye las URLs para la vista de dashboards
    path('inventario/', include('inventario.urls')),  # Incluye las URLs para la vista de inventario
    path('carrito/', include('carrito.urls')),  # Incluye las URLs de la aplicación carrito de compras
    path('usuarios/', include('usuarios.urls')),  # Incluye las URLs de la aplicación usuarios
    path('bodega/', include('bodega.urls')), # Incluye las URLs de la aplicación bodega
    path('facturacion/', include('facturacion.urls')), # Incluye las URLs de la aplicación facturación
    path('configuracion/', include('configuracion.urls', namespace='configuracion')),  # Incluye las URLs de la aplicación configuración
    path('', tienda_views.index, name='index'),  # Página de inicio en el proyecto
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Asocia las vistas de error a los manejadores globales
handler400 = 'cascos_mac.views.bad_request'
handler403 = 'cascos_mac.views.forbidden'
handler404 = 'cascos_mac.views.not_found'
handler500 = 'cascos_mac.views.server_error'
handler405 = 'cascos_mac.views.error_405_view'
handler408 = 'cascos_mac.views.error_408_view'
handler503 = 'cascos_mac.views.error_503_view'