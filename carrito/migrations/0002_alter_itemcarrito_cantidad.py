# Generated by Django 5.1 on 2025-02-16 20:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carrito', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemcarrito',
            name='cantidad',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
