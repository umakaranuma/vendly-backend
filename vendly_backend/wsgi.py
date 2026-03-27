"""
WSGI config for the vendly_backend project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
import pymysql
pymysql.install_as_MySQLdb()

from django.core.wsgi import get_wsgi_application

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vendly_backend.settings.base")

application = get_wsgi_application()
app = application

