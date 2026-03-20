from __future__ import annotations

import asyncio
import logging
import random
from datetime import timedelta

import mServices.ResponseService as ResponseService
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mServices.ValidatorService import ValidatorService
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from vendly_backend.models import CoreRole, CoreStatus, CoreUser, Vendor

try:
    from pingram import Pingram
except Exception:  # pragma: no cover - optional dependency at runtime
    Pingram = None


logger = logging.getLogger(__name__)


OTP_CACHE_PREFIX = "auth:otp"


def _build_tokens_for_user(user: CoreUser) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def _otp_cache_key(user_id: int) -> str:
    return f"{OTP_CACHE_PREFIX}:{user_id}"


def _generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


async def _send_pingram_sms(phone: str, otp_code: str) -> None:
    if not settings.PINGRAM_API_KEY:
        raise RuntimeError("PINGRAM_API_KEY is not configured.")
    if Pingram is None:
        raise RuntimeError("pingram-python package is not installed.")

    async with Pingram(
        api_key=settings.PINGRAM_API_KEY,
        base_url=settings.PINGRAM_BASE_URL,
    ) as client:
        await client.send(
            {
                "type": "alert",
                "to": {
                    "id": phone,
                    "number": phone,
                },
                "sms": {
                    "message": f"Your verification code is: {otp_code}. Reply STOP to opt-out.",
                },
            }
        )


def _send_registration_otp(user: CoreUser) -> None:
    otp_code = _generate_otp()
    expires_in = int(getattr(settings, "OTP_EXPIRES_IN_SECONDS", 600))
    expires_at = timezone.now() + timedelta(seconds=expires_in)

    cache.set(
        _otp_cache_key(user.id),
        {
            "otp_code": otp_code,
            "expires_at": expires_at.isoformat(),
        },
        timeout=expires_in,
    )

    asyncio.run(_send_pingram_sms(user.phone or "", otp_code))


def _user_payload(user: CoreUser) -> dict:
    role = user.role
    role_payload = None
    if role:
        role_payload = {"id": role.id, "name": role.name, "description": role.description}
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": role_payload,
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

    # Validate required fields via ValidatorService
    errors = ValidatorService.validate(
        data,
        rules={
            "email": "required|email",
            "phone": "required",
            "password": "required|min:6",
            "first_name": "required",
        },
        custom_messages={
            "password.required": "Password is required.",
            "password.min": "Password must be at least 6 characters.",
            "email.email": "Email must be a valid address.",
            "email.required": "Email is required.",
            "phone.required": "Phone is required.",
            "first_name.required": "Name is required.",
        },
    )
    if errors:
        return ResponseService.response(
            "VALIDATION_ERROR",
            errors,
            "Validation Error",
        )

    if email and CoreUser.objects.filter(email=email).exists():
        return ResponseService.response(
            "CONFLICT",
            {"email": ["Email already registered."]},
            "Validation Error",
        )
    if phone and CoreUser.objects.filter(phone=phone).exists():
        return ResponseService.response(
            "CONFLICT",
            {"phone": ["Phone already registered."]},
            "Validation Error",
        )

    role, _ = CoreRole.objects.get_or_create(name="CUSTOMER")

    try:
        with transaction.atomic():
            user = CoreUser.objects.create_user(
                email=email,
                phone=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
            )

            # Admin “user card” status (active by default).
            user.status_ref = CoreStatus.objects.get_or_create(
                status_type="customer_active",
                defaults={"entity_type": "customer", "name": "active", "sort_order": 10},
            )[0]
            user.save(update_fields=["status_ref"])
            _send_registration_otp(user)
    except Exception as exc:
        logger.exception("Failed sending registration OTP for customer: %s", exc)
        return ResponseService.response(
            "SERVER_ERROR",
            {"detail": "Unable to send OTP right now. Please try again."},
            "Registration failed.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return ResponseService.response(
        "SUCCESS",
        {
            "user": _user_payload(user),
            "otp_sent": True,
            "otp_expires_in_seconds": int(getattr(settings, "OTP_EXPIRES_IN_SECONDS", 600)),
        },
        "Customer registered successfully. Please confirm OTP.",
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

    name = data.get("store_name") or data.get("name") # support legacy clients
    city = data.get("city", "")

    # Validate required vendor fields via ValidatorService
    errors = ValidatorService.validate(
        data,
        rules={
            "email": "required|email",
            "phone": "required",
            "password": "required|min:6",
        },
        custom_messages={
            "email.required": "Email is required.",
            "email.email": "Email must be a valid address.",
            "phone.required": "Phone is required.",
            "password.required": "Password is required.",
            "password.min": "Password must be at least 6 characters.",
        },
    )
    # Validate name after resolving legacy store_name/name field
    if not name:
        errors = errors or {}
        errors.setdefault("name", []).append("Name is required.")

    if errors:
        return ResponseService.response(
            "VALIDATION_ERROR",
            errors,
            "Validation Error",
        )

    if email and CoreUser.objects.filter(email=email).exists():
        return ResponseService.response(
            "CONFLICT",
            {"email": ["Email already registered."]},
            "Validation Error",
        )
    if phone and CoreUser.objects.filter(phone=phone).exists():
        return ResponseService.response(
            "CONFLICT",
            {"phone": ["Phone already registered."]},
            "Validation Error",
        )

    role, _ = CoreRole.objects.get_or_create(name="VENDOR")

    try:
        with transaction.atomic():
            pending_status, _ = CoreStatus.objects.get_or_create(
                status_type="vendor_pending",
                defaults={"entity_type": "vendor", "name": "pending", "sort_order": 10},
            )

            user = CoreUser.objects.create_user(
                email=email,
                phone=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
            )

            # Admin “user card” status (active by default).
            user.status_ref = CoreStatus.objects.get_or_create(
                status_type="customer_active",
                defaults={"entity_type": "customer", "name": "active", "sort_order": 10},
            )[0]
            user.save(update_fields=["status_ref"])

            Vendor.objects.create(
                user=user,
                name=name,
                city=city,
                status="pending",
                status_ref=pending_status,
            )
            _send_registration_otp(user)
    except Exception as exc:
        logger.exception("Failed sending registration OTP for vendor: %s", exc)
        return ResponseService.response(
            "SERVER_ERROR",
            {"detail": "Unable to send OTP right now. Please try again."},
            "Registration failed.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return ResponseService.response(
        "SUCCESS",
        {
            "user": _user_payload(user),
            "otp_sent": True,
            "otp_expires_in_seconds": int(getattr(settings, "OTP_EXPIRES_IN_SECONDS", 600)),
        },
        "Vendor registered successfully. Please confirm OTP.",
        status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    data = request.data
    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""

    # Validate login input; password required, at least one of email/phone required
    errors = ValidatorService.validate(
        data,
        rules={
            "password": "required",
        },
        custom_messages={
            "password.required": "Password is required.",
        },
    )

    if not email and not phone:
        errors = errors or {}
        errors.setdefault("contact", []).append("Either email or phone is required.")

    if errors:
        return ResponseService.response(
            "VALIDATION_ERROR",
            errors,
            "Validation Error",
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

    if not user.is_verified:
        return ResponseService.response(
            "FORBIDDEN",
            {"detail": _("Please verify OTP to complete registration.")},
            "Login failed.",
            status.HTTP_403_FORBIDDEN,
        )

    if not user.is_active:
        return ResponseService.response(
            "FORBIDDEN",
            {"detail": _("User account is disabled.")},
            "Login failed.",
            status.HTTP_403_FORBIDDEN,
        )

    tokens = _build_tokens_for_user(user)

    return ResponseService.response(
        "SUCCESS",
        {"tokens": tokens, "user": _user_payload(user)},
        "Login successful.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def confirm_registration_otp(request: Request) -> Response:
    data = request.data
    otp_code = (data.get("otp") or "").strip()
    user_id = data.get("user_id")

    errors = ValidatorService.validate(
        data,
        rules={
            "user_id": "required",
            "otp": "required",
        },
        custom_messages={
            "user_id.required": "User id is required.",
            "otp.required": "OTP is required.",
        },
    )
    if errors:
        return ResponseService.response(
            "VALIDATION_ERROR",
            errors,
            "Validation Error",
        )

    try:
        user = CoreUser.objects.get(id=user_id)
    except CoreUser.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {"detail": "User not found."},
            "Verification failed.",
            status.HTTP_404_NOT_FOUND,
        )

    otp_data = cache.get(_otp_cache_key(user.id))
    if not otp_data:
        return ResponseService.response(
            "UNAUTHORIZED",
            {"detail": "OTP expired or not found. Please register again."},
            "Verification failed.",
            status.HTTP_401_UNAUTHORIZED,
        )

    if str(otp_data.get("otp_code")) != otp_code:
        return ResponseService.response(
            "UNAUTHORIZED",
            {"detail": "Invalid OTP."},
            "Verification failed.",
            status.HTTP_401_UNAUTHORIZED,
        )

    user.is_verified = True
    user.save(update_fields=["is_verified"])
    cache.delete(_otp_cache_key(user.id))

    tokens = _build_tokens_for_user(user)
    return ResponseService.response(
        "SUCCESS",
        {"tokens": tokens, "user": _user_payload(user)},
        "OTP confirmed. Registration completed successfully.",
        status.HTTP_200_OK,
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me_view(request: Request) -> Response:
    user = request.user
    assert isinstance(user, CoreUser)

    if request.method == "PATCH":
        data = request.data

        # Validate updatable profile fields (all optional, but typed)
        errors = ValidatorService.validate(
            data,
            rules={
                "first_name": "nullable",
                "last_name": "nullable",
                "phone": "nullable",
            },
            custom_messages={},
        )
        if errors:
            return ResponseService.response(
                "VALIDATION_ERROR",
                errors,
                "Validation Error",
            )

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

