# Generated by Django 5.1 on 2025-02-27 15:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0006_remove_venta_iva'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='metodo_pago',
            field=models.CharField(choices=[('NEQUI', 'Nequi'), ('DAVIPLATA', 'Daviplata'), ('PSE', 'PSE'), ('TARJETA', 'Tarjeta de Crédito'), ('EFECTIVO', 'Efectivo')], default='EFECTIVO', max_length=25),
        ),
    ]
