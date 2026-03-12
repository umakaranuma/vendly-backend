"""
WSGI config for the vendly_backend project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vendly_backend.settings.base")

application = get_wsgi_application()

