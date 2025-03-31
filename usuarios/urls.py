# usuarios/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import *

urlpatterns = [
    path('login/', login_page, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Recuperar contraseña 
    path(
        'recuperar/password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='recuperar/password_reset_form.html',
            email_template_name='recuperar/password_reset_email.html'
        ),
        name='password_reset'
    ),
    path(
        'recuperar/password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='recuperar/password_reset_done.html'),
        name='password_reset_done'
    ),
    path(
        'recuperar/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='recuperar/password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    path(
        'recuperar/reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='recuperar/password_reset_complete.html'),
        name='password_reset_complete'
    ),

    # Perfil
    path('mi-perfil/', UsuarioDetailView.as_view(), name='mi_perfil'),
    path('<int:pk>/detalle/', DetalleDeUsuarioView.as_view(), name='detalle_usuario'),

    # Vistas de CRUD Usuarios
    path('listar/', ListarUsuariosView.as_view(), name='listar_usuarios'),
    path('crear/', CrearUsuarioView.as_view(), name='crear_usuario'),
    path('editar/<int:pk>/', EditarUsuarioView.as_view(), name='editar_usuario'),
    path('eliminar/<int:pk>/', EliminarUsuarioView.as_view(), name='eliminar_usuario'),
]
