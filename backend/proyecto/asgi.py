"""
ASGI config for proyecto project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import sys

from django.core.asgi import get_asgi_application

# Agrega backend/proyecto/ al path para que Python encuentre el paquete 'escuela'
# (mismo ajuste que hace manage.py; necesario cuando se corre asgi.py directo).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'proyecto'))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')

application = get_asgi_application()
