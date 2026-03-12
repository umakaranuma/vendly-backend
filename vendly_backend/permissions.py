from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsVendor(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user.role, "name", "").upper() == "VENDOR")


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        role_name = getattr(user.role, "name", "").upper() if user and user.is_authenticated else ""
        return bool(user and user.is_authenticated and role_name in {"ADMIN", "SUPER_ADMIN"})


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        role_name = getattr(user.role, "name", "").upper() if user and user.is_authenticated else ""
        return bool(user and user.is_authenticated and role_name == "SUPER_ADMIN")

