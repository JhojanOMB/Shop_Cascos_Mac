from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from .forms import CustomAuthenticationForm
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.db.models import Q  # Importación de Q
from .models import *
from .forms import *
from django.http import JsonResponse
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin

def login_page(request):
    if request.user.is_authenticated:
        return redirect_user_based_on_role(request.user)
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            auth_login(request, user)
            return redirect_user_based_on_role(user)
        else:
            messages.error(request, 'Credenciales inválidas. Por favor verifica tu correo o usuario y contraseña.')
            # Guarda el valor ingresado para mantenerlo en el formulario tras redirigir
            request.session['username_or_email'] = request.POST.get('username_or_email', '')
            return redirect('login')  # PRG para evitar reenvío del formulario
    else:
        # Si hay dato almacenado en sesión, lo usa como valor inicial
        initial_data = {}
        if 'username_or_email' in request.session:
            initial_data['username_or_email'] = request.session.pop('username_or_email')
        form = CustomAuthenticationForm(initial=initial_data)
    
    return render(request, 'login.html', {'form': form})


def redirect_user_based_on_role(user):
    roles_redirects = {
        'gerente': 'dashboard_gerente',
        'vendedor': 'dashboard_vendedor',
    }
    return redirect(roles_redirects.get(user.rol, 'index'))



def logout_view(request):
    auth_logout(request)
    return redirect('login')


class ListarUsuariosView(LoginRequiredMixin, ListView):
    login_url = 'login'  # Redirige si no está autenticado
    model = Usuario
    template_name = 'dashboard/usuarios/listar_usuarios.html'
    context_object_name = 'usuarios'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        # Verificar que el usuario tenga el rol requerido, por ejemplo "directivo"
        if request.user.rol != 'gerente':
            return render(request, 'errores/403.html', status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        rol = self.request.GET.get('rol', '')
        queryset = Usuario.objects.all()
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) | Q(email__icontains=query)
            )
        if rol:
            queryset = queryset.filter(rol=rol)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class CrearUsuarioView(LoginRequiredMixin,SuccessMessageMixin, CreateView):
    login_url = 'login'  # Redirige si no está autenticado
    model = Usuario
    template_name = 'dashboard/usuarios/crear_usuario.html'
    success_url = reverse_lazy('listar_usuarios')
    form_class = CrearUsuarioForm

    def form_valid(self, form):
        # Guarda el usuario y la contraseña de forma segura
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password1'])  # Hashea la contraseña
        user.save()

        # Añadir la bandera de éxito al contexto
        return self.render_to_response(
            self.get_context_data(form=form, success=True)
        )
    
    def form_invalid(self, form):
        # Manejar errores
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{form.fields[field].label or field}: {error}")
        return self.render_to_response(self.get_context_data(form=form))
    
class EditarUsuarioView(LoginRequiredMixin,UpdateView):
    login_url = 'login'  # Redirige si no está autenticado
    model = Usuario
    template_name = 'dashboard/usuarios/editar_usuario.html'
    form_class = EditarUsuarioForm
    success_url = reverse_lazy('listar_usuarios')

    def form_valid(self, form):
        # Guardar los cambios
        form.save()

        # Añadir la bandera de éxito al contexto
        return self.render_to_response(
            self.get_context_data(form=form, success=True)
        )

    def form_invalid(self, form):
        # Manejar errores
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{form.fields[field].label or field}: {error}")
        return self.render_to_response(self.get_context_data(form=form))
class EliminarUsuarioView(LoginRequiredMixin,DeleteView):
    login_url = 'login'  # Redirige si no está autenticado
    model = Usuario
    template_name = 'dashboard/usuarios/eliminar_usuario.html'
    success_url = reverse_lazy('listar_usuarios')

class UsuarioDetailView(LoginRequiredMixin, DetailView):
    login_url = 'login'  # Redirige si no está autenticado
    model = Usuario
    template_name = 'dashboard/usuarios/perfil.html'
    
    # Sobrescribe el método para usar el usuario autenticado
    def get_object(self):
        return self.request.user
    
class DetalleDeUsuarioView(LoginRequiredMixin, DetailView):
    login_url = 'login'  # Redirige si no está autenticado
    model = Usuario
    template_name = 'dashboard/usuarios/detalle_usuario.html'
    context_object_name = 'usuario'