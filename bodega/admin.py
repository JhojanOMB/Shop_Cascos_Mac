from django.contrib import admin
from .models import Bodega, StockBodega

@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion')

@admin.register(StockBodega)
class StockBodegaAdmin(admin.ModelAdmin):
    list_display = ('producto', 'bodega', 'cantidad')
    list_filter = ('bodega',)