# dashboards/urls.py
from django.urls import path
from . import views
from .views import *
from django.conf.urls.static import static

urlpatterns = [    
    # Dashboard por roles
    path('dashboards/gerente/', views.dashboard_gerente, name='dashboard_gerente'),
    path('dashboards/vendedor/', views.dashboard_vendedor, name='dashboard_vendedor'),
    path("ayuda/", ayuda, name="ayuda"),

]

