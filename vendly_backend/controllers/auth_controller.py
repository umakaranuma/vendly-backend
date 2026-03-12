from __future__ import annotations

import mServices.ResponseService as ResponseService
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from vendly_backend.models import CoreRole, CoreUser, VendorProfile


def _build_tokens_for_user(user: CoreUser) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def register_customer(request: Request) -> Response:
    data = request.data
    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    if not email and not phone:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Either email or phone is required."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    if not password or len(password) < 6:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Password must be at least 6 characters."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    if email and CoreUser.objects.filter(email=email).exists():
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Email already registered."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )
    if phone and CoreUser.objects.filter(phone=phone).exists():
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Phone already registered."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    role, _ = CoreRole.objects.get_or_create(name="CUSTOMER")

    user = CoreUser.objects.create_user(
        email=email,
        phone=phone,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )

    tokens = _build_tokens_for_user(user)
    user_payload = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": {"id": role.id, "name": role.name, "description": role.description},
    }
    return ResponseService.response(
        "SUCCESS",
        {"tokens": tokens, "user": user_payload},
        "Customer registered successfully.",
        status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_vendor(request: Request) -> Response:
    data = request.data
    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    store_name = data.get("store_name")
    business_name = data.get("business_name", "")
    address = data.get("address", "")
    city = data.get("city", "")
    state = data.get("state", "")
    country = data.get("country", "")
    postal_code = data.get("postal_code", "")
    contact_email = data.get("contact_email", "")
    contact_phone = data.get("contact_phone", "")

    if not email and not phone:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Either email or phone is required."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    if not password or len(password) < 6:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Password must be at least 6 characters."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    if not store_name:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Store name is required."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    if email and CoreUser.objects.filter(email=email).exists():
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Email already registered."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )
    if phone and CoreUser.objects.filter(phone=phone).exists():
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Phone already registered."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    role, _ = CoreRole.objects.get_or_create(name="VENDOR")

    with transaction.atomic():
        user = CoreUser.objects.create_user(
            email=email,
            phone=phone,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

        VendorProfile.objects.create(
            user=user,
            store_name=store_name,
            business_name=business_name,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )

    tokens = _build_tokens_for_user(user)
    user_payload = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": {"id": role.id, "name": role.name, "description": role.description},
    }
    return ResponseService.response(
        "SUCCESS",
        {"tokens": tokens, "user": user_payload},
        "Vendor registered successfully.",
        status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    data = request.data
    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""

    if not email and not phone:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Either email or phone is required."},
            "Validation failed.",
            status.HTTP_400_BAD_REQUEST,
        )

    user: CoreUser | None = None

    if email:
        try:
            user = CoreUser.objects.get(email=email)
        except CoreUser.DoesNotExist:
            user = None
    elif phone:
        try:
            user = CoreUser.objects.get(phone=phone)
        except CoreUser.DoesNotExist:
            user = None

    if not user or not user.check_password(password):
        return ResponseService.response(
            "UNAUTHORIZED",
            {"detail": _("Unable to log in with provided credentials.")},
            "Login failed.",
            status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return ResponseService.response(
            "FORBIDDEN",
            {"detail": _("User account is disabled.")},
            "Login failed.",
            status.HTTP_403_FORBIDDEN,
        )

    tokens = _build_tokens_for_user(user)

    role = user.role
    role_payload = None
    if role:
        role_payload = {"id": role.id, "name": role.name, "description": role.description}

    user_payload = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": role_payload,
    }

    return ResponseService.response(
        "SUCCESS",
        {"tokens": tokens, "user": user_payload},
        "Login successful.",
        status.HTTP_200_OK,
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me_view(request: Request) -> Response:
    user = request.user
    assert isinstance(user, CoreUser)

    if request.method == "PATCH":
        data = request.data
        # Only allow some fields to be updated
        for field in ["first_name", "last_name", "phone"]:
            if field in data:
                setattr(user, field, data.get(field))
        user.save(update_fields=["first_name", "last_name", "phone"])
        message = "Profile updated successfully."
    else:
        message = "Profile fetched successfully."

    role = user.role
    role_payload = None
    if role:
        role_payload = {"id": role.id, "name": role.name, "description": role.description}

    user_payload = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": role_payload,
    }

    return ResponseService.response(
        "SUCCESS",
        user_payload,
        message,
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request: Request) -> Response:
    refresh_token = request.data.get("refresh")
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            # If blacklist is not enabled or token invalid, ignore.
            pass

    return ResponseService.response(
        "SUCCESS",
        {},
        "Logged out successfully.",
        status.HTTP_200_OK,
    )

