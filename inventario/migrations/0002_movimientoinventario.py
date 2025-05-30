# Generated by Django 5.1 on 2025-04-12 02:26

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0001_initial'),
        ('tienda', '0022_alter_categoria_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MovimientoInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.IntegerField(help_text='Para ingresos y salidas indica el valor absoluto. Para ajuste, el nuevo total.')),
                ('motivo', models.CharField(choices=[('ingreso', 'Ingreso'), ('salida', 'Salida'), ('ajuste', 'Ajuste')], max_length=20)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('comentario', models.TextField(blank=True, null=True)),
                ('producto_talla', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimientos', to='tienda.productotalla')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
