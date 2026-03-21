from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission


def is_admin_user(user: Any) -> bool:
    """
    True for CoreRole ADMIN/SUPER_ADMIN, or Django superusers (e.g. createsuperuser)
    who may not have a CoreRole row set.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    role_name = ""
    role = getattr(user, "role", None)
    if role is not None:
        role_name = getattr(role, "name", "") or ""
    return role_name.upper() in {"ADMIN", "SUPER_ADMIN"}


def is_super_admin_user(user: Any) -> bool:
    """True for role SUPER_ADMIN or Django superuser."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    role = getattr(user, "role", None)
    if role is None:
        return False
    return (getattr(role, "name", "") or "").upper() == "SUPER_ADMIN"


class IsVendor(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user.role, "name", "").upper() == "VENDOR")


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_super_admin_user(request.user)

