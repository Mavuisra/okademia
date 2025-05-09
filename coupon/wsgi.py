"""
WSGI config for coupon project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys
import traceback
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon.settings')

# Initialiser l'application Django standard
application = get_wsgi_application()

# Exécuter le script d'initialisation
try:
    from init_app import init_app
    init_app()
    print("Application initialisée avec succès.")
except Exception as e:
    print(f"Erreur lors de l'initialisation de l'application: {str(e)}")
    traceback.print_exc()
    # Ne pas interrompre le démarrage de l'application en cas d'erreur
