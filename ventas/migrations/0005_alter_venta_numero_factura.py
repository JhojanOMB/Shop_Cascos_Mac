# Generated by Django 5.1 on 2025-02-12 23:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0004_venta_qr_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='venta',
            name='numero_factura',
            field=models.CharField(blank=True, max_length=36, null=True, unique=True),
        ),
    ]
