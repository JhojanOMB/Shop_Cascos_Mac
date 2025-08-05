# configuracion/urls.py
from django.urls import path
from .views import ui_settings

app_name = 'configuracion'

urlpatterns = [
    path('ui-settings/', ui_settings, name='ui_settings'),
]
