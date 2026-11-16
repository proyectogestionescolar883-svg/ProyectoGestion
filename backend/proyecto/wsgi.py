"""
WSGI config for proyecto project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

# Agrega backend/proyecto/ al path para que Python encuentre el paquete 'escuela'
# (mismo ajuste que hace manage.py; necesario cuando se corre wsgi.py directo,
# por ejemplo en Vercel).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')

application = get_wsgi_application()
