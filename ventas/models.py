# ventas/models.py
from django.conf import settings
from django.db import models,transaction  # Para manejar transacciones atómicas
from django.utils.timezone import now
from tienda.models import *
from django.core.exceptions import ValidationError
from PIL import Image
import qrcode
import uuid
from django.conf import settings
import os
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

# Modelo dinámico para métodos de pago
class MetodoPago(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


METODOS_PAGO = (
    ('NEQUI', 'Nequi'),
    ('DAVIPLATA', 'Daviplata'),
    ('PSE', 'PSE'),
    ('TARJETA', 'Tarjeta de Crédito'),
    ('EFECTIVO', 'Efectivo'),
    ('ADDI', 'ADDI'),
    ('SISTECREDITO', 'Sistecredito'),
)

# Modelo de Venta
class Venta(models.Model):
    empleado       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cliente        = models.CharField(max_length=255, blank=True, null=True)
    fecha          = models.DateTimeField(default=timezone.now)
    total          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    numero_factura = models.CharField(max_length=36, unique=True, blank=True, null=True)
    facturado      = models.BooleanField(default=False)
    facturada_electronicamente = models.BooleanField(default=False)
    qr_code        = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    metodo_pago    = models.CharField(max_length=25, choices=METODOS_PAGO, default='EFECTIVO')
    anulado        = models.BooleanField(default=False)

    def __str__(self):
        return f"Factura {self.numero_factura or 'Sin Factura'} - Total: ${self.total} - Empleado: {self.empleado}"

    def calcular_total(self):
        # Suma los totales de los detalles relacionados
        self.total = sum(det.total for det in self.detalles.all())

    def generate_qr_code(self):
        url = f"https://mi-tienda.com/consultar-factura/{self.numero_factura}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        img_filename = f"qrcode-{self.numero_factura}.png"
        img_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
        os.makedirs(img_dir, exist_ok=True)
        img_path = os.path.join(img_dir, img_filename)
        img.save(img_path)

        # Guardamos la ruta relativa para ImageField
        self.qr_code = os.path.join('qrcodes', img_filename)

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        with transaction.atomic():
            # 1) Si es nueva, guardamos para obtener ID y luego asignar número de factura
            if is_new:
                super().save(*args, **kwargs)
                self.numero_factura = str(uuid.uuid4())
                super().save(update_fields=['numero_factura'])

            # 2) Calculamos total y guardamos TODOS los campos modificados
            self.calcular_total()
            super().save(*args, **kwargs)

            # 3) Generamos QR si aún no existe
            if not self.qr_code:
                self.generate_qr_code()
                super().save(update_fields=['qr_code'])

# Modelo de Detalle de Venta
class DetalleVenta(models.Model):
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, related_name='detalles')
    producto_talla = models.ForeignKey(ProductoTalla, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
    )
    codigo_barras = models.CharField(max_length=13, blank=True, null=True)
    anulado = models.BooleanField(default=False)

    def calcular_total(self):
        """Calcula el total del detalle multiplicando la cantidad por el precio."""
        self.total = self.cantidad * self.precio

    def descontar_inventario(self):
        """Descuenta la cantidad especificada del inventario si hay suficiente stock."""
        if self.producto_talla.cantidad >= self.cantidad:
            self.producto_talla.cantidad -= self.cantidad
            self.producto_talla.save()
        else:
            raise ValidationError('No hay suficiente inventario para este producto en la talla seleccionada.')

    def save(self, *args, **kwargs):
        """Guarda el detalle de venta, calculando el total, sin afectar inventario automáticamente."""
        with transaction.atomic():
            self.calcular_total()

            # Ya no se llama descontar_inventario aquí

            if not self.codigo_barras:
                self.codigo_barras = self.producto_talla.codigo_barras

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Factura {self.venta.numero_factura or 'Sin Factura'} - Total: ${self.total} - Empleado: {self.venta.empleado} - Método de Pago: {self.venta.get_metodo_pago_display()}"

class CajaDiaria(models.Model):
    fecha = models.DateField(unique=True, default=timezone.now)
    apertura = models.DecimalField("Saldo apertura", max_digits=12, decimal_places=2, default=0)
    gastos = models.DecimalField("Total gastos", max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"Caja {self.fecha}"

    @property
    def ventas_totales(self):
        # Suponiendo que tienes un modelo Venta con un campo total y fecha
        from ventas.models import Venta
        return Venta.objects.filter(fecha=self.fecha).aggregate(
            suma=Sum('total')
        )['suma'] or 0

    @property
    def neto(self):
        # Saldo apertura + ventas – gastos
        return self.apertura + self.ventas_totales - self.gastos
    
class VentaBorrador(models.Model):
    usuario     = models.ForeignKey(User, on_delete=models.CASCADE)
    creado_en   = models.DateTimeField(auto_now_add=True)

    def total(self):
        return sum(d.subtotal() for d in self.detalles.all())

class DetalleBorrador(models.Model):
    venta_borrador = models.ForeignKey(VentaBorrador, related_name='detalles', on_delete=models.CASCADE)
    producto_talla = models.ForeignKey(ProductoTalla, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def subtotal(self):
        precio_base = self.producto_talla.producto.precio_venta
        return precio_base * self.cantidad