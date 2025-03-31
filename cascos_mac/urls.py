from django.contrib import admin
from django.urls import path, include
from tienda import views as tienda_views
from usuarios import views as usuarios_views
from inventario.views import inventario_view
from carrito.views import *  # Importamos las vistas del carrito de compras
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', usuarios_views.login_page, name='login'),
    path('logout/', usuarios_views.logout_view, name='logout'),
    path('tienda/', include('tienda.urls')),  # Incluye las URLs de la aplicación tienda
    path('ventas/', include('ventas.urls')),  # Incluye las URLs de la aplicación ventas
    path('inventario/', inventario_view, name='inventario'),  # URL para la vista de inventario
    path('carrito/', include('carrito.urls')),  # Incluye las URLs de la aplicación carrito de compras
    path('usuarios/', include('usuarios.urls')),  # Incluye las URLs de la aplicación usuarios
    path('', tienda_views.index, name='index'),  # Página de inicio en el proyecto
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
