from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
from django.db import transaction  # Para manejar transacciones atómicas
from usuarios.models import Usuario
from django.utils.timezone import now
from inventario.models import *
from django.apps import apps

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Proveedor(models.Model):
    nombre = models.CharField(max_length=50)
    provedor_de = models.CharField(max_length=255, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    correo_electronico = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Talla(models.Model):
    nombre = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.nombre

class ProductoTalla(models.Model):
    producto = models.ForeignKey('Producto', related_name='producto_tallas', on_delete=models.CASCADE)
    talla = models.ForeignKey(Talla, related_name='producto_tallas', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=False)
    codigo_barras = models.CharField(max_length=13, unique=True, blank=True, null=True)  # Campo para el código de barras

    class Meta:
        unique_together = ('producto', 'talla')  # Evitar duplicados para el mismo producto y talla

    def save(self, *args, **kwargs):
        # Generar automáticamente un código de barras si no existe
        if not self.codigo_barras:
            # Combinar la referencia del producto con el ID de la talla para generar un código único
            referencia = self.producto.referencia or str(uuid.uuid4().hex[:12]).upper()
            talla_id = f"{self.talla.id:03}"  # Asegura que el ID de la talla tenga siempre 3 dígitos
            # Crear una base de 12 dígitos (combinación de referencia y talla)
            base_codigo = (referencia + talla_id)[-12:]  # Ajustar al tamaño máximo de 12 caracteres
            # Asegurarse de que el código base sea numérico
            base_codigo = ''.join([c for c in base_codigo if c.isdigit()])[:12]
            base_codigo = base_codigo.zfill(12)  # Completa con ceros a la izquierda si es necesario
            self.codigo_barras = self.generar_codigo_ean13(base_codigo)
        super().save(*args, **kwargs)

    @staticmethod
    def generar_codigo_ean13(base_codigo):
        """
        Genera un código de barras válido en formato EAN-13 calculando el dígito verificador.
        """
        if len(base_codigo) != 12 or not base_codigo.isdigit():
            raise ValueError("El código base debe ser numérico y tener exactamente 12 caracteres.")
        suma_impares = sum(int(base_codigo[i]) for i in range(0, 12, 2))
        suma_pares = sum(int(base_codigo[i]) for i in range(1, 12, 2))
        checksum = (10 - ((suma_impares + suma_pares * 3) % 10)) % 10
        return f"{base_codigo}{checksum}"

    def __str__(self):
        return f"{self.producto.nombre} - {self.talla.nombre} - Cantidad: {self.cantidad} - Código: {self.codigo_barras}"

class Producto(models.Model):

    GENERO_CHOICES = [
        ('', 'Seleccione una opción'),
        ('caballero', 'Caballero'),
        ('dama', 'Dama'),
        ('unisex', 'Unisex'),
        ('no_necesita', 'No necesita')
    ]

    referencia = models.CharField(max_length=12, unique=True, blank=True, null=True)
    codigo_barras = models.CharField(max_length=13, unique=True, blank=True, null=True)
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=0)  # Precio de venta
    categoria = models.ForeignKey('Categoria', on_delete=models.CASCADE, related_name='productos')
    cantidad = models.PositiveIntegerField(default=0)  # Cantidad de producto si no requiere tallas

    # Imágenes del producto
    imagen1 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen2 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen3 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen4 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen5 = models.ImageField(upload_to='productos/', blank=True, null=True)

    # Género del producto
    genero = models.CharField(
        max_length=15,
        choices=GENERO_CHOICES,
        blank=True,
        null=True
    )

    CATALOG_CHOICES = [
        ('', 'Seleccione una opción'),
        ('catalogo', 'En Catálogo'),
        ('no_catalogo', 'No Catálogo'),
    ]
    
    catalogo = models.CharField(
        max_length=15,
        choices=CATALOG_CHOICES,
        default='no_catalogo',
    )

    # Ofertas
    en_oferta = models.BooleanField(default=False)
    precio_oferta = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)

    # Costo y proveedor
    precio_compra = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)
    proveedor = models.ForeignKey('Proveedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')

    # Fecha de creación
    created_date = models.DateField(auto_now_add=True)

    def generar_referencia(self):
        """
        Genera una referencia basada en una parte del nombre del producto y una secuencia.
        Por ejemplo, para un producto llamado "Casco Shaft Pro", se podría generar:
            CAS-0001
        """
        # Tomamos las 3 primeras letras del nombre; si el nombre es muy corto, completamos con la palabra completa.
        prefijo = self.nombre[:3].upper()
        # Contamos los productos que ya tienen una referencia que inicia con ese prefijo
        secuencia = Producto.objects.filter(referencia__startswith=prefijo).count() + 1
        return f"{prefijo}-{secuencia:04}"  # Formato: "CAS-0001"

    def clean(self):
        # Validar que el precio de venta no sea negativo ni esté vacío
        if self.precio_venta is None or self.precio_venta < 0:
            raise ValidationError({'precio_venta': 'El precio de venta no puede ser negativo ni estar vacío.'})

        # Validar la lógica de la oferta
        if self.en_oferta:
            if self.precio_oferta is None:
                raise ValidationError({'precio_oferta': 'Debe especificar un precio de oferta si el producto está en oferta.'})
            if self.precio_oferta >= self.precio_venta:
                raise ValidationError({'precio_oferta': 'El precio de oferta debe ser menor que el precio de venta.'})

    def save(self, *args, **kwargs):
        # Convertir el nombre a Title Case (por ejemplo, "Casco Shaft Pro")
        if self.nombre:
            self.nombre = self.nombre.title()
        
        # Generar la referencia única si no existe
        if not self.referencia:
            self.referencia = self.generar_referencia()

        # Generar el código de barras único si no existe
        if not self.codigo_barras:
            self.codigo_barras = str(uuid.uuid4().int)[:13]

        # Validar la lógica definida en el método clean
        self.full_clean()

        # Guardar la instancia
        super().save(*args, **kwargs)

    def calcular_costo_total_pedido(self):
        """
        Calcula el costo total del pedido basado en el precio de compra 
        y las cantidades de las tallas asociadas.
        """
        if self.precio_compra:
            return self.precio_compra * self.calcular_total_cantidad()
        return 0

    def calcular_total_cantidad(self):
        """
        Calcula el total de productos sumando las cantidades 
        de cada talla asociada al producto.
        """
        if self.producto_tallas.exists():
            return sum(detalle.cantidad for detalle in self.producto_tallas.all())
        return 0

    @property
    def tiene_descuento(self):
        """
        Propiedad para verificar si el producto tiene descuento activo.
        """
        return self.en_oferta and self.precio_oferta < self.precio_venta

    def __str__(self):
        return f"{self.nombre} - Ref: {self.referencia}"
    
    @property
    def cantidades_por_talla(self):
        cantidades = {}
        for detalle in self.producto_tallas.filter(activa=True):
            cantidades[detalle.talla.nombre] = detalle.cantidad
        return cantidades

    @property
    def total_cantidad(self):
        """
        Retorna la cantidad total de productos sumando todas las tallas.
        """
        return sum(detalle.cantidad for detalle in self.producto_tallas.all())
