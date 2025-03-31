from django import forms
from django.contrib.auth import authenticate
from .models import *
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import UserCreationForm

class CustomAuthenticationForm(forms.Form):
    username_or_email = forms.CharField(
        label='Nombre de Usuario o Correo Electrónico',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get('username_or_email', '').strip().lower()
        password = cleaned_data.get('password')

        if username_or_email and password:
            # Busca por username o email
            user = Usuario.objects.filter(
                models.Q(username__iexact=username_or_email) |
                models.Q(email__iexact=username_or_email)
            ).first()

            if user:
                # Autenticación del usuario
                authenticated_user = authenticate(username=user.username, password=password)
                if authenticated_user:
                    cleaned_data['user'] = authenticated_user
                else:
                    if not user.is_active:
                        raise forms.ValidationError('Esta cuenta está inactiva. Contacta al administrador.')
                    raise forms.ValidationError('La contraseña es incorrecta.')
            else:
                raise forms.ValidationError('No existe una cuenta con este nombre de usuario o correo electrónico.')
        else:
            raise forms.ValidationError('Por favor, completa todos los campos.')

        return cleaned_data


class CrearUsuarioForm(UserCreationForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'rol']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        # Verificar si las contraseñas coinciden
        if password1 != password2:
            raise ValidationError("Las contraseñas no coinciden.")
        
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)

        # Si las contraseñas coinciden, las seteamos
        if self.cleaned_data['password1']:
            user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()
        return user
    
class EditarUsuarioForm(UserChangeForm):
    password1 = forms.CharField(
        label="Nueva Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ingresa una nueva contraseña'}),
        required=False
    )
    password2 = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirma la nueva contraseña'}),
        required=False
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'rol']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)

        # Si se ingresa una nueva contraseña, la actualiza
        if self.cleaned_data['password1']:
            user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
        return user