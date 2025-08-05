# configuracion/context_processors.py

import os, json
from django.conf import settings

def ui_colors(request):
    """
    Lee el JSON de configuración de colores si existe
    y lo combina con los valores por defecto en settings.UI_COLORS.
    Devuelve {'UI_COLORS': {...}} para las plantillas.
    """
    cfg_file = os.path.join(settings.BASE_DIR, 'ui_settings.json')
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, 'r') as f:
                saved = json.load(f)
        except json.JSONDecodeError:
            saved = {}
    else:
        saved = {}
    # Combina valores por defecto + guardados
    merged = settings.UI_COLORS.copy()
    for k, v in saved.items():
        if k in merged:
            merged[k] = v
    return {'UI_COLORS': merged}

def ui_configuracion(request):
    return {
        'UI_COLORS': settings.UI_COLORS,
        'UI_ICON_MAP': settings.UI_ICON_MAP,
        'UI_PERMISSIONS': settings.UI_PERMISSIONS,
    }