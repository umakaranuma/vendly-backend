"""
ASGI config for the vendly_backend project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vendly_backend.settings.base")

application = get_asgi_application()

