# Generated by Django 5.1 on 2024-12-17 05:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0002_producto_imagen4'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='imagen5',
            field=models.ImageField(blank=True, null=True, upload_to='productos/'),
        ),
    ]
