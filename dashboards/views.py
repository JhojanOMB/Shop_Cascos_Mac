from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.utils.timezone import now
from django.db.models.functions import ExtractMonth
from ventas.models import *
from ventas.forms import *
from tienda.models import *
from django.utils import timezone
import locale


from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta



@login_required
def dashboard_gerente(request):
    # — Fecha local en Bogotá —
    current_date = timezone.localdate()
    current_year  = current_date.year
    current_month = current_date.month

    # — Caja diaria —
    caja, _ = CajaDiaria.objects.get_or_create(fecha=current_date)

    # — Formularios con prefijos —
    form_apertura = CajaDiariaForm(request.POST or None,
                                   instance=caja,
                                   prefix='apertura')
    form_gastos   = CajaDiariaForm(request.POST or None,
                                   instance=caja,
                                   prefix='gastos')

    # — Procesar POST —
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'apertura' and form_apertura.is_valid():
            form_apertura.save()
            return redirect('ventas:dashboard_gerente')
        if action == 'gasto' and form_gastos.is_valid():
            form_gastos.save()
            return redirect('ventas:dashboard_gerente')

    # — Ventas del día (fecha local) —
    ventas_del_dia      = Venta.objects.filter(fecha__date=current_date)
    total_ventas_dia    = ventas_del_dia.aggregate(total=Sum('total'))['total'] or 0
    cantidad_ventas_dia = ventas_del_dia.count()

    # — 1) Detalle de productos vendidos hoy —
    productos_hoy = (
        ventas_del_dia
        .values(
            nombre=F('detalles__producto_talla__producto__nombre'),
            forma_pago=F('metodo_pago'),   # <-- alias distinto
        )
        .annotate(
            cantidad=Sum('detalles__cantidad'),
            subtotal=Sum('detalles__total'),
        )
        .order_by('-cantidad')
    )

    # — 2) Métodos de pago usados hoy —
    metodos_pago = (
        ventas_del_dia
        .values('metodo_pago')
        .annotate(
            veces=Count('id'),
            monto=Sum('total')
        )
        .order_by('-monto')
    )

    # — Ventas mensuales —
    ventas_por_mes = (
        Venta.objects.filter(fecha__year=current_year)
        .annotate(month=ExtractMonth('fecha'))
        .values('month')
        .annotate(total=Sum('total'))
        .order_by('month')
    )
    ventas_mensuales = {m: 0 for m in range(1, 13)}
    for v in ventas_por_mes:
        ventas_mensuales[v['month']] = v['total']
    total_mes_actual   = ventas_mensuales[current_month]
    mes_anterior       = current_month - 1 if current_month > 1 else 12
    total_mes_anterior = ventas_mensuales[mes_anterior]

    if total_mes_anterior > 0:
        porcentaje_diferencia = ((total_mes_actual - total_mes_anterior) / total_mes_anterior) * 100
    elif total_mes_actual > 0:
        porcentaje_diferencia = 100
    else:
        porcentaje_diferencia = 0

    # — Mejor vendedor del mes —
    mejor_vendedor_qs = (
        Venta.objects
        .filter(fecha__year=current_year, fecha__month=current_month)
        .values('empleado__first_name', 'empleado__last_name')
        .annotate(total_empleado=Sum('total'))
        .order_by('-total_empleado')
    )
    if mejor_vendedor_qs:
        mejor = mejor_vendedor_qs[0]
        mejor_vendedor_nombre = f"{mejor['empleado__first_name']} {mejor['empleado__last_name']}"
        mejor_vendedor_total  = mejor['total_empleado']
    else:
        mejor_vendedor_nombre = None
        mejor_vendedor_total  = 0

    # — Stock —
    productos_bajo_stock = Producto.objects.filter(
        producto_tallas__cantidad__lte=5
    ).distinct()
    productos_sin_stock  = Producto.objects.filter(
        producto_tallas__cantidad=0
    ).distinct()

    # — Cantidad ventas mes actual —
    cantidad_ventas_mes_actual = Venta.objects.filter(
        fecha__year=current_year,
        fecha__month=current_month
    ).count()

    return render(request, 'dashboard_gerente.html', {
        'form_apertura': form_apertura,
        'form_gastos': form_gastos,
        'caja': caja,
        'neto': caja.neto,

        # Datos diarios
        'total_ventas_dia': total_ventas_dia,
        'cantidad_ventas_dia': cantidad_ventas_dia,
        'productos_hoy': productos_hoy,
        'metodos_pago': metodos_pago,

        # Datos mensuales
        'total_ventas_mes_actual': total_mes_actual,
        'porcentaje_diferencia': round(porcentaje_diferencia, 2),
        'cantidad_ventas_mes_actual': cantidad_ventas_mes_actual,
        'ventas_mensuales': ventas_mensuales,

        # Mejor vendedor
        'mejor_vendedor_nombre': mejor_vendedor_nombre,
        'mejor_vendedor_total': mejor_vendedor_total,

        # Stock
        'productos_bajo_stock': productos_bajo_stock,
        'productos_sin_stock': productos_sin_stock,

        # Context extras
        'current_date': current_date,
        'show_sidebar': True,
    })

# Vista del dashboard para el vendedor
@login_required
def dashboard_vendedor(request):
    # Forzar español Colombia
    locale.setlocale(locale.LC_TIME, 'es_CO.UTF-8')

    # Obtener todos los productos y ventas
    productos = Producto.objects.all()
    ventas = Venta.objects.all()

    # Filtrar productos con bajo stock (cantidad <= 5) y sin stock (cantidad == 0)

    # Obtener la fecha actual
    today = timezone.now()  # Obtener la fecha y hora actual
        # Consultar las ventas agrupadas por mes del año actual

    monthly_data = ventas.filter(fecha__year=today.year) \
        .extra(select={'month': "strftime('%%m', fecha)"}) \
        .values('month') \
        .annotate(total=Sum('total')) \
        .order_by('month')

    # Nombres de meses en español
    nombres_meses = {
        '01': "Enero", '02': "Febrero", '03': "Marzo", '04': "Abril", '05': "Mayo", '06': "Junio",
        '07': "Julio", '08': "Agosto", '09': "Septiembre", '10': "Octubre", '11': "Noviembre", '12': "Diciembre"
    }
        # Inicializa listas con 0 para cada mes
    monthly_values = {str(i).zfill(2): 0 for i in range(1, 13)}  # Diccionario con 0 para cada mes

    # Rellenar los valores con los datos reales de ventas
    for data in monthly_data:
        month = data['month']  # Mes como string '01', '02', ..., '12'
        total = data['total'] or 0  # Total de ventas del mes (0 si no hay ventas)
        monthly_values[month] = total  # Asigna el total de ventas al mes correspondiente

    # Obtener el mes actual y mes pasado
    mes_actual = today.month
    mes_pasado = mes_actual - 1 if mes_actual > 1 else 12  # Si es enero, el mes pasado es diciembre

    # Obtener los totales de ventas para los meses actual y pasado
    total_ventas_mes_actual = monthly_values[str(mes_actual).zfill(2)]  # Ventas del mes actual

        # Cantidad de ventas realizadas este mes
    cantidad_ventas_mes_actual = ventas.filter(fecha__year=today.year, fecha__month=mes_actual).count()

    # Pasar las variables al contexto para renderizar en el template
    context = {
        'productos': productos,
        'ventas': ventas,
        'total_ventas_mes_actual': total_ventas_mes_actual,
        'cantidad_ventas_mes_actual': cantidad_ventas_mes_actual,
        'mes_actual': nombres_meses[str(mes_actual).zfill(2)],  # Mes actual en formato legible
        'mes_pasado': nombres_meses[str(mes_pasado).zfill(2)],  # Mes pasado en formato legible
        'show_sidebar': True,  # Para mostrar la barra lateral
    }

    return render(request, 'dashboard_vendedor.html', context)

@login_required
def ayuda(request):
    return render(request, 'dashboard/ayuda/ayuda.html', {
        'show_sidebar': True,
    })
