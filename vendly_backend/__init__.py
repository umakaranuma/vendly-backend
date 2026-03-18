"""
vendly_backend package.

We install PyMySQL as a drop-in replacement for MySQLdb to avoid native
mysqlclient/libmysql issues across environments (especially Windows).
"""

from __future__ import annotations

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except Exception:
    # If PyMySQL isn't installed (e.g. during some tooling steps), Django will
    # fall back to the configured DB backend imports and raise a clear error.
    pass

