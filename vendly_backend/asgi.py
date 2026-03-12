"""
ASGI config for the vendly_backend project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from django.core.asgi import get_asgi_application

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vendly_backend.settings.base")

application = get_asgi_application()

