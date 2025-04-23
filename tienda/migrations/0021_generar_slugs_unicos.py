from django.db import migrations
from django.utils.text import slugify

def generate_unique_slug(model, instance, base_slug):
    slug = base_slug
    num = 1
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{num}"
        num += 1
    return slug

def set_unique_slugs(apps, schema_editor):
    Producto = apps.get_model('tienda', 'Producto')
    for producto in Producto.objects.all():
        if not producto.slug:
            base_slug = slugify(producto.nombre)
            producto.slug = generate_unique_slug(Producto, producto, base_slug)
            producto.slug = slugify(base_slug)  # Asegurarse de que esté bien formateado
            producto.save()

class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0020_producto_slug'),
    ]

    operations = [
        migrations.RunPython(set_unique_slugs),
    ]
