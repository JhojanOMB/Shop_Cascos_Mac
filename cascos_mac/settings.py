import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-0ee!fl%7vm)6@&!-g)hn4uh_5+wtn5e_m#&h2$l0s)j++t=!5='

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "217.196.48.97",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",  # Para entorno local
    "http://127.0.0.1:8000",  # Para entorno local
]

# Aplicaciones instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # Para servir archivos estáticos en desarrollo
    'django.contrib.humanize',

    #aplicaciones locales
    'tienda.apps.TiendaConfig',
    'usuarios.apps.UsuariosConfig',
    'inventario.apps.InventarioConfig',
    'ventas.apps.VentasConfig',
    'carrito.apps.CarritoConfig',
    'dashboards.apps.DashboardsConfig',
    'bodega.apps.BodegaConfig',
    'facturacion.apps.FacturacionConfig',
    'configuracion.apps.ConfiguracionConfig',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'cascos_mac.urls'

# Configuración de plantillas
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],  # Este es para templates globales en la raíz del proyecto
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                
                'carrito.context_processors.carrito_total_items',
                'carrito.context_processors.cart_context',
                'configuracion.context_processors.ui_configuracion',
                'configuracion.context_processors.ui_colors',
                'configuracion.menu.menu_items',  # Context processor para el menú
            ],
        },
    },
]

WSGI_APPLICATION = 'cascos_mac.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internacionalización
LANGUAGE_CODE = 'es-co'  # Código de idioma (Español de Colombia)
TIME_ZONE = 'America/Bogota'  # Zona horaria
USE_I18N = True
USE_TZ = True

# Archivos estáticos (CSS, JavaScript, Imágenes)
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # Directorio donde se recopilan los archivos estáticos
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Campo de clave primaria predeterminado
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'usuarios.Usuario'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Usa la base de datos para almacenar sesiones
SESSION_COOKIE_NAME = 'sessionid'  # Nombre de la cookie de sesión
SESSION_COOKIE_AGE = 1209600  # Duración de la cookie en segundos (2 semanas por defecto)
SESSION_SAVE_EVERY_REQUEST = True  # Guarda la sesión en cada solicitud

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Configuración de íconos (Font Awesome)
UI_ICON_MAP = {
    'dashboard': 'fa-house',
    'inventario': 'fa-boxes',
    'bodega': 'fa-warehouse',
    'productos': 'fa-box',
    'categorias': 'fa-tags',
    'ventas': 'fa-shopping-cart',
    'usuarios': 'fa-users',
    'proveedores': 'fa-truck',
    'adicionales': 'fa-layer-group',
    'perfil': 'fa-user',
    'facturacion': 'fa-paper-plane',
    'configuracion': 'fa-cog',  # icono para configuración
    'ayuda': 'fa-circle-question',
}

# Configuración de colores (clases Tailwind)
UI_COLORS = {
    'sidebar_bg': 'bg-gray-100',
    'sidebar_text': 'text-white-700',
    'sidebar_hover': 'hover:bg-gray-200',
    'navbar_bg': 'bg-gray-800',
    'navbar_text': 'text-white',
    'button_bg': 'bg-gray-700',
    'button_hover': 'hover:bg-gray-600',
    'mobile_menu_bg': 'bg-white',
    'config_panel_bg': 'bg-white',
    'config_panel_text': 'text-gray-800',
}

# Permisos por rol
UI_PERMISSIONS = {
    'gerente': [
        'dashboard','inventario','bodega','productos','categorias',
        'ventas','usuarios','proveedores','adicionales','perfil','facturacion','configuracion', 'ayuda'
    ],
    'vendedor': [
        'dashboard','inventario','bodega','productos','adicionales','perfil','configuracion', 'ayuda'
    ],
}

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True    