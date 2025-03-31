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


# Opciones de pago

METODOS_PAGO = (
    ('NEQUI', 'Nequi'),
    ('DAVIPLATA', 'Daviplata'),
    ('PSE', 'PSE'),
    ('TARJETA', 'Tarjeta de Crédito'),
    ('EFECTIVO', 'Efectivo'),
)

# Modelo de Venta
class Venta(models.Model):
    empleado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    numero_factura = models.CharField(max_length=36, unique=True, blank=True, null=True)  # Aumentamos la longitud
    facturado = models.BooleanField(default=False)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    metodo_pago = models.CharField(max_length=25, choices=METODOS_PAGO, default='EFECTIVO')

    def calcular_total(self):
        self.total = sum(detalle.total for detalle in self.detalles.all())

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.numero_factura:
                super().save(*args, **kwargs)
                self.numero_factura = str(uuid.uuid4())  # Generamos un UUID completo
                super().save(update_fields=['numero_factura'])
            self.calcular_total()
            super().save(update_fields=['total'])

            if not self.qr_code:
                self.generate_qr_code()
                super().save(update_fields=['qr_code'])

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
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
        img_path = os.path.join(img_dir, img_filename)
        
        img.save(img_path)
        self.qr_code = os.path.join('qrcodes', img_filename)

    def __str__(self):
        return f"Factura {self.numero_factura or 'Sin Factura'} - Total: ${self.total} - Empleado: {self.empleado}"

# Modelo de Detalle de Venta
class DetalleVenta(models.Model):
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, related_name='detalles')
    producto_talla = models.ForeignKey(ProductoTalla, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    codigo_barras = models.CharField(max_length=13, blank=True, null=True)

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
        """Guarda el detalle de venta con la lógica de cálculo y descuento de inventario."""
        with transaction.atomic():
            self.calcular_total()
            self.descontar_inventario()

            if not self.codigo_barras:
                self.codigo_barras = self.producto_talla.codigo_barras

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Factura {self.venta.numero_factura or 'Sin Factura'} - Total: ${self.total} - Empleado: {self.venta.empleado} - Método de Pago: {self.venta.get_metodo_pago_display()}"
