from django.contrib import admin
from .models import *
from django.core.exceptions import ValidationError
from django.db.models import Sum

# venta y detalleventa son solo uno en el admin
admin.site.register(Venta)
admin.site.register(DetalleVenta)