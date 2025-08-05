# configuracion/views.py
from pathlib import Path
import json
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse

from .forms import UISettingsForm

@staff_member_required
def ui_settings(request):
    config_path = Path(settings.BASE_DIR) / 'ui_settings.json'

    try:
        if config_path.exists():
            saved = json.loads(config_path.read_text(encoding='utf-8'))
        else:
            saved = {}  # valores por defecto vacíos
    except (json.JSONDecodeError, OSError):
        saved = {}

    if request.method == 'POST':
        form = UISettingsForm(request.POST)
        if form.is_valid():
            new_colors = {key: form.cleaned_data[key] for key in form.fields}
            config_path.write_text(json.dumps(new_colors, indent=2, ensure_ascii=False), encoding='utf-8')
            messages.success(request, "Configuración guardada correctamente.")
            return redirect(reverse('configuracion:ui_settings'))
        else:
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = UISettingsForm(initial=saved)

    return render(request, 'dashboard/configuracion/ui_settings.html', {
        'form': form,
        'current_settings': saved,
    })
