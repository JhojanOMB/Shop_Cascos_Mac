# Generated by Django 5.1 on 2025-04-10 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0019_alter_talla_options_alter_color_codigo_hex_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='slug',
            field=models.SlugField(blank=True, null=True),
        ),
    ]
