from django.db import models
from django.contrib.auth import get_user_model
from ventas.models import Venta

User = get_user_model()


class ConfiguracionFacturaElectronica(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Usuario"
    )
    nit = models.CharField("NIT", max_length=15)
    razon_social = models.CharField("Razón Social", max_length=255)
    certificado = models.FileField("Certificado Digital (.p12)", upload_to='certificados/')
    contrasena_certificado = models.CharField("Contraseña del Certificado", max_length=100)
    software_id = models.CharField("Software ID", max_length=100)
    pin = models.CharField("PIN del Software", max_length=10)
    habilitado = models.BooleanField("¿Habilitado para Facturación?", default=True)
    modo = models.CharField(
        "Modo DIAN",
        max_length=20,
        choices=[('produccion', 'Producción'), ('pruebas', 'Pruebas')],
        default='produccion'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Facturación Electrónica"
        verbose_name_plural = "Configuraciones de Facturación Electrónica"

    def __str__(self):
        return f"{self.razon_social} ({'Activo' if self.habilitado else 'Inactivo'})"


class FacturaElectronica(models.Model):
    venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name='factura_electronica'
    )
    numero_cufe = models.CharField("CUFE", max_length=100, blank=True, null=True)
    xml = models.TextField("XML generado", blank=True, null=True)
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente'),
            ('enviada', 'Enviada'),
            ('aceptada', 'Aceptada'),
            ('rechazada', 'Rechazada'),
            ('error', 'Error')
        ],
        default='pendiente'
    )
    respuesta_dian = models.TextField("Respuesta DIAN", blank=True, null=True)
    fecha_envio = models.DateTimeField("Fecha de Envío", auto_now_add=True)

    class Meta:
        verbose_name = "Factura Electrónica"
        verbose_name_plural = "Facturas Electrónicas"

    def __str__(self):
        return f"Factura #{self.venta.id} - {self.get_estado_display()}"
