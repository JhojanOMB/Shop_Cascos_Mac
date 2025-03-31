# usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    EMAIL_FIELD = 'email'

    # Opciones para el campo rol
    ROLES = (
        ('', 'Seleccione una opción'),
        ('gerente', 'Gerente'),
        ('vendedor', 'Vendedor'),
    )

    email = models.EmailField(unique=True)
    rol = models.CharField(
        max_length=20,
        choices=ROLES,
    )

    def __str__(self):
        return self.username

    def is_gerente(self):
        return self.rol == 'gerente'

    def is_vendedor(self):
        return self.rol == 'vendedor'
    
    def save(self, *args, **kwargs):
        self.email = self.email.lower()  # Asegura que el correo se guarde en minúsculas
        super().save(*args, **kwargs)