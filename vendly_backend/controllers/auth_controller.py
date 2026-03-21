from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import timedelta

import mServices.ResponseService as ResponseService
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mServices.ValidatorService import ValidatorService
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from vendly_backend.models import CoreRole, CoreStatus, CoreUser, Vendor
from vendly_backend.permissions import is_admin_user

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


def _phone_from_registration_data(data) -> str | None:
    """Resolve `phone` or `mobile` so OTP SMS targets the number the client sent (customer + vendor register)."""
    return (data.get("phone") or data.get("mobile") or "").strip() or None


def _data_with_phone_for_validation(data, phone: str | None):
    """Merge resolved phone into the payload so `phone|required` passes when only `mobile` was sent."""
    if isinstance(data, dict):
        merged = dict(data)
        if phone is not None:
            merged["phone"] = phone
        return merged
    if hasattr(data, "copy"):
        merged = data.copy()
        if phone is not None:
            merged["phone"] = phone
        return merged
    return data


def _generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


def _normalize_phone_for_sms(phone: str) -> str:
    """
    Pingram SMS delivery expects a proper mobile destination. Prefer E.164 (e.g. +919876543210).
    Do not pass the phone as Pingram `to.id` — that field is a user id and can resolve the wrong recipient.
    """
    raw = (phone or "").strip()
    if not raw:
        return ""
    if raw.startswith("+"):
        digits = re.sub(r"\D", "", raw[1:])
        return f"+{digits}" if digits else ""
    digits_only = re.sub(r"\D", "", raw)
    if not digits_only:
        return ""
    if len(digits_only) == 12 and digits_only.startswith("91"):
        return f"+{digits_only}"
    if len(digits_only) == 10 and digits_only[0] in "6789":
        return f"+91{digits_only}"
    return f"+{digits_only}"


async def _send_pingram_sms(phone: str, otp_code: str) -> None:
    if not settings.PINGRAM_API_KEY:
        raise RuntimeError("PINGRAM_API_KEY is not configured.")
    if Pingram is None:
        raise RuntimeError("pingram-python package is not installed.")

    to_number = _normalize_phone_for_sms(phone)
    if not to_number:
        raise RuntimeError("Phone number is missing; cannot send OTP SMS.")

    async with Pingram(
        api_key=settings.PINGRAM_API_KEY,
        base_url=settings.PINGRAM_BASE_URL,
    ) as client:
        payload = {
            # Only `number` for ad-hoc SMS — `id` is a Pingram user id and can target the wrong contact.
            "to": {"number": to_number},
            "forceChannels": ["SMS"],
            "sms": {
                "message": f"Your verification code is: {otp_code}. Reply STOP to opt-out.",
            },
        }
        response = None
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.send(payload)
                break
            except Exception as exc:
                status_code = getattr(exc, "status", None) or getattr(exc, "status_code", None)
                is_retryable = status_code in {502, 503, 504}
                if not is_retryable or attempt == max_attempts:
                    raise
                logger.warning(
                    "Pingram temporary failure while sending OTP. attempt=%s status=%s number=%s error=%s",
                    attempt,
                    status_code,
                    to_number,
                    exc,
                )
                await asyncio.sleep(0.8 * attempt)

        if response is None:
            raise RuntimeError("Pingram SMS response missing after retries.")
        tracking_id = getattr(response, "tracking_id", None)
        messages = getattr(response, "messages", None) or []
        logger.info(
            "Pingram OTP SMS accepted. number=%s tracking_id=%s messages=%s",
            to_number,
            tracking_id,
            messages,
        )
        # Pingram can acknowledge accepted delivery with tracking_id even when messages is empty.
        # Fail only when both tracking metadata and messages are missing.
        if not tracking_id and not messages:
            raise RuntimeError("Pingram did not return tracking_id/messages for OTP SMS.")


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
@authentication_classes([])
@permission_classes([AllowAny])
def register_customer(request: Request) -> Response:
    data = request.data
    email = (data.get("email") or "").strip() or None
    phone = _phone_from_registration_data(data)
    password = data.get("password") or ""
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    # Validate required fields via ValidatorService
    errors = ValidatorService.validate(
        _data_with_phone_for_validation(data, phone),
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
@authentication_classes([])
@permission_classes([AllowAny])
def register_vendor(request: Request) -> Response:
    data = request.data
    email = (data.get("email") or "").strip() or None
    phone = _phone_from_registration_data(data)
    password = data.get("password") or ""
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    name = data.get("store_name") or data.get("name") # support legacy clients
    city = data.get("city", "")

    # Validate required vendor fields via ValidatorService
    errors = ValidatorService.validate(
        _data_with_phone_for_validation(data, phone),
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
@authentication_classes([])
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
@authentication_classes([])
@permission_classes([AllowAny])
def admin_login_view(request: Request) -> Response:
    """
    JWT login for staff dashboard clients. Same credentials shape as /api/auth/login.
    Allowed: CoreRole ADMIN/SUPER_ADMIN, or Django superuser (createsuperuser).
    Does not require OTP verification for accounts outside the customer/vendor registration flow.
    """
    data = request.data
    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""

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
            user = CoreUser.objects.select_related("role").get(email=email)
        except CoreUser.DoesNotExist:
            user = None
    elif phone:
        try:
            user = CoreUser.objects.select_related("role").get(phone=phone)
        except CoreUser.DoesNotExist:
            user = None

    if not user or not user.check_password(password):
        return ResponseService.response(
            "UNAUTHORIZED",
            {"detail": _("Unable to log in with provided credentials.")},
            "Login failed.",
            status.HTTP_401_UNAUTHORIZED,
        )

    if not is_admin_user(user):
        return ResponseService.response(
            "FORBIDDEN",
            {"detail": _("Admin privileges required.")},
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
        "Admin login successful.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([])
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

