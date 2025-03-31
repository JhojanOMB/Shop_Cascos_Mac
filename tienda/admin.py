from django.contrib import admin
from .models import *
from django.core.exceptions import ValidationError
from django.db.models import Sum

admin.site.register(Producto)
admin.site.register(ProductoTalla)
admin.site.register(Categoria)
admin.site.register(Talla)
admin.site.register(Proveedor)
