from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from tienda.models import Producto
from .models import Bodega, StockBodega
from .forms import *

@login_required
def contenido_bodegas(request):
    bodegas = Bodega.objects.all()
    return render(request, 'dashboard/bodega/bodega_contenido.html', {'bodegas': bodegas})

@login_required
def detalle_bodega(request, pk):
    bodega = get_object_or_404(Bodega, pk=pk)
    stocks = bodega.stocks.select_related('producto')
    return render(request, 'dashboard/bodega/detalles_bodega.html', {'bodega': bodega, 'stocks': stocks})

@login_required
def transferir_stock(request):
    if request.method == 'POST':
        form = TransferenciaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contenido_bodegas')
    else:
        form = TransferenciaForm()
    return render(request, 'dashboard/bodega/transferir_bodega.html', {'form': form})

@login_required
def crear_bodega(request):
    if request.method == 'POST':
        form = BodegaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contenido_bodegas')
    else:
        form = BodegaForm()
    return render(request, 'dashboard/bodega/crear_bodega.html', {'form': form})

@login_required
def editar_bodega(request, pk):
    bodega = get_object_or_404(Bodega, pk=pk)
    if request.method == 'POST':
        form = BodegaForm(request.POST, instance=bodega)
        if form.is_valid():
            form.save()
            return redirect('detalle_bodega', pk=bodega.pk)
    else:
        form = BodegaForm(instance=bodega)
    return render(request, 'dashboard/bodega/editar_bodega.html', {'form': form, 'bodega': bodega})
