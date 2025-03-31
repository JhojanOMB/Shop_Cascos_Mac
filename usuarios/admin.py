# usuarios/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Usuario

class UserCreationFormCustom(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'rol')

class UserChangeFormCustom(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'rol')

class UsuarioAdmin(BaseUserAdmin):
    form = UserChangeFormCustom
    add_form = UserCreationFormCustom

    list_display = ('username', 'first_name', 'last_name', 'email', 'rol')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    filter_horizontal = ()

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'rol')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'rol'),
        }),
    )

admin.site.register(Usuario, UsuarioAdmin)
