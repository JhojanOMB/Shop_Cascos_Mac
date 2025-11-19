# configuracion/menu.py
from django.conf import settings

def menu_items(request):
    items = []
    if request.user.is_authenticated:
        all_items = [
            # key,           url_name
            ('dashboard',    'dashboard_gerente' if request.user.rol=='gerente' else 'dashboard_vendedor'),
            ('inventario',   'inventario'),
            ('bodega',       'contenido_bodegas'),
            ('productos',    'contenido_productos'),
            ('categorias',   'contenido_categorias'),
            ('ventas',       'ventas:contenido_ventas'),
            ('usuarios',     'listar_usuarios' if request.user.rol=='gerente' else 'mi_perfil'),
            ('proveedores',  'contenido_proveedores'),
            ('adicionales',  'contenido_adicionales'),
            ('perfil',       'mi_perfil'),
            ('facturacion',  'facturacion:configurar_facturacion'),
            ('configuracion', 'configuracion:ui_settings'),
            ('ayuda',     'ayuda'),
        ]
        for key, url_name in all_items:
            if key in settings.UI_PERMISSIONS.get(request.user.rol, []):
                items.append((key, url_name))
    return {'menu_items': items}
