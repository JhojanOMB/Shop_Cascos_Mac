# app tienda

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
from django.db import transaction  # Para manejar transacciones atómicas
from usuarios.models import Usuario
from django.utils.timezone import now
from inventario.models import *
from django.apps import apps
import re
from django.utils.text import slugify

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['nombre']  # Ordena por el campo nombre de forma ascendente

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
    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Color(models.Model):
    nombre = models.CharField(max_length=50)
    codigo_hex = models.CharField(max_length=7, default='#000000')

    def __str__(self):
        return self.nombre

class Producto(models.Model):

    GENERO_CHOICES = [
        ('', 'Seleccione una opción'),
        ('caballero', 'Caballero'),
        ('dama', 'Dama'),
        ('unisex', 'Unisex'),
        ('no_necesita', 'No necesita')
    ]

    referencia = models.CharField(max_length=12, unique=True, blank=True, null=True)
    nombre = models.CharField(
        max_length=100,
        unique=True,
        error_messages={
            'unique': "Ya existe un Producto con este Nombre.",
        }
    )
    slug = models.SlugField(unique=False, blank=True, null=True)
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

    @staticmethod
    def generate_unique_slug(instance, slug_field='slug', from_field='nombre'):
        slug_base = slugify(getattr(instance, from_field))
        unique_slug = slug_base
        ModelClass = instance.__class__
        counter = 1

        while ModelClass.objects.filter(**{slug_field: unique_slug}).exists():
            unique_slug = f"{slug_base}-{counter}"
            counter += 1

        return unique_slug

    def generar_referencia(self):
        """
        Genera una referencia única basada en una parte limpia del nombre del producto.
        Ejemplo: para un producto llamado "Casco Shaft Pro", se genera: CAS-0001
        """
        import re
        nombre_clean = re.sub(r'[^A-Za-z]', '', self.nombre)
        prefijo = nombre_clean[:3].upper()

        secuencia = 1
        while True:
            referencia = f"{prefijo}-{secuencia:04}"
            if not Producto.objects.filter(referencia=referencia).exists():
                return referencia
            secuencia += 1

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
        # Convertir el nombre a Title Case
        if self.nombre:
            self.nombre = self.nombre.title()

        # Generar la referencia única si no existe
        if not self.referencia:
            self.referencia = self.generar_referencia()

        # Generar el slug único si no existe
        if not self.slug:
            self.slug = Producto.generate_unique_slug(self)

        # Validar la lógica definida en clean
        self.full_clean()
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
    def detalles_por_talla_color_genero(self):
        """Retorna todos los detalles (talla, color, género y cantidad) asociados al producto."""
        detalles = []
        for detalle in self.producto_tallas.all():
            detalles.append({
                'talla': detalle.talla.nombre,
                'color': detalle.color.nombre,
                'genero': detalle.genero,
                'cantidad': detalle.cantidad
            })
        return detalles

    @property
    def total_cantidad(self):
        """
        Retorna la cantidad total de productos sumando todas las tallas.
        """
        return sum(detalle.cantidad for detalle in self.producto_tallas.all())
    
    @property
    def imagen_miniatura(self):
        if self.imagen1:
            return self.imagen1.url
        return '/static/img/No_hay_imagen.png'
    
    @property
    def tallas_disponibles(self):
        """
        Devuelve los objetos ProductoTalla activos y con stock > 0.
        """
        return self.producto_tallas.filter(activa=True, cantidad__gt=0).select_related('talla', 'color')

class ProductoTalla(models.Model):
    producto = models.ForeignKey('Producto', related_name='producto_tallas', on_delete=models.CASCADE)
    talla = models.ForeignKey(Talla, related_name='producto_tallas', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE, blank=True, null=True)
    genero = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        choices=Producto.GENERO_CHOICES,
        default='no_necesita'
    )
    cantidad = models.PositiveIntegerField(default=0)
    codigo_barras = models.CharField(max_length=13, unique=True, blank=True, null=True)
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ('producto', 'talla', 'color', 'genero')

    def save(self, *args, **kwargs):
        # Generar automáticamente un código de barras si no existe
        if not self.codigo_barras:
            self.codigo_barras = self.generar_codigo_unico()
        super().save(*args, **kwargs)

    def generar_codigo_unico(self):
        """
        Genera un código EAN-13 único basado en referencia, talla y UUID si es necesario.
        """
        base_codigo = self.crear_base_codigo()
        codigo = self.generar_codigo_ean13(base_codigo)

        # Asegurar unicidad
        while ProductoTalla.objects.filter(codigo_barras=codigo).exists():
            base_codigo = self.crear_base_codigo(extra_uuid=True)
            codigo = self.generar_codigo_ean13(base_codigo)

        return codigo

    def crear_base_codigo(self, extra_uuid=False):
        """
        Crea una base de 12 dígitos para generar un EAN-13.
        Si extra_uuid es True, se añade un UUID para asegurar unicidad.
        """
        referencia = self.producto.referencia or ""
        talla_id = f"{self.talla.id:03}" if self.talla_id else "000"

        base = referencia + talla_id
        if extra_uuid:
            base += str(uuid.uuid4().int)

        base_numerica = ''.join(filter(str.isdigit, base))[:12]
        return base_numerica.zfill(12)

    @staticmethod
    def generar_codigo_ean13(base_codigo):
        """
        Genera el dígito verificador del código EAN-13.
        """
        if len(base_codigo) != 12 or not base_codigo.isdigit():
            raise ValueError("El código base debe tener exactamente 12 dígitos numéricos.")
        suma_impares = sum(int(base_codigo[i]) for i in range(0, 12, 2))
        suma_pares = sum(int(base_codigo[i]) for i in range(1, 12, 2))
        checksum = (10 - ((suma_impares + suma_pares * 3) % 10)) % 10
        return f"{base_codigo}{checksum}"

    def __str__(self):
        producto = self.producto.nombre if self.producto else "Sin producto"
        talla = self.talla.nombre if self.talla else "Sin talla"
        color = self.color.nombre if self.color else "Sin color"
        genero = self.genero if self.genero else "Sin género"
        cantidad = self.cantidad if self.cantidad is not None else "Sin cantidad"
        codigo = self.codigo_barras if self.codigo_barras else "Sin código"
        return f"{producto} - Talla: {talla} - Color: {color} - Género: {genero} - Cantidad: {cantidad} - Código: {codigo}"
