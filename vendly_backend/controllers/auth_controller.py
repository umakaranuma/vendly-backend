from __future__ import annotations

import logging
import time
import random
import re
from datetime import timedelta

import mServices.ResponseService as ResponseService
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import UploadedFile
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

from vendly_backend.activity_log import log_activity
from vendly_backend.models import CoreRole, CoreStatus, CoreUser, Vendor
from vendly_backend.permissions import is_admin_user
from vendly_backend.supabase_media import (
    MediaValidationError,
    SupabaseNotConfiguredError,
    upload_django_file,
)

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

logger = logging.getLogger(__name__)


OTP_CACHE_PREFIX = "auth:otp"
# Registration OTP is fixed (SMS disabled). Must match what clients send to confirm-otp.
STATIC_REGISTRATION_OTP = "111111"


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
    Twilio SMS expects E.164 (e.g. +94769114278, +919876543210).
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


def _send_twilio_sms(phone: str, otp_code: str) -> None:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN are not configured.")
    if not settings.TWILIO_PHONE_NUMBER:
        raise RuntimeError("TWILIO_PHONE_NUMBER is not configured.")

    to_number = _normalize_phone_for_sms(phone)
    if not to_number:
        raise RuntimeError("Phone number is missing; cannot send OTP SMS.")

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    body = f"Your verification code is: {otp_code}. Reply STOP to opt-out."

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            message = client.messages.create(
                body=body,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_number,
            )
            logger.info(
                "Twilio OTP SMS sent. number=%s sid=%s status=%s",
                to_number,
                message.sid,
                message.status,
            )
            return
        except TwilioRestException as exc:
            status_code = exc.status
            is_retryable = status_code in {500, 502, 503, 504}
            if not is_retryable or attempt == max_attempts:
                raise
            logger.warning(
                "Twilio temporary failure while sending OTP. attempt=%s status=%s number=%s error=%s",
                attempt,
                status_code,
                to_number,
                exc,
            )
            time.sleep(0.8 * attempt)


def _send_registration_otp(user: CoreUser) -> None:
    otp_code = STATIC_REGISTRATION_OTP
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


def _account_type_from_role(user: CoreUser) -> str:
    """Lowercase role name for clients (e.g. customer, vendor)."""
    if user.role and user.role.name:
        return user.role.name.strip().lower()
    return "unknown"


def _vendor_business_payload(vendor: Vendor) -> dict:
    """
    Business profile from `vendors` + `categories`.
    Business display name is `vendors.name` (maps to API field `business_name`).
    """
    cat = vendor.category
    category_payload = None
    if cat:
        category_payload = {"id": cat.id, "name": cat.name, "slug": cat.slug}
    return {
        "id": vendor.id,
        "slug": vendor.slug,
        "business_name": vendor.name,
        "name": vendor.name,
        "city": vendor.city,
        "bio": vendor.bio,
        "category_id": vendor.category_id,
        "category": category_payload,
        "status": vendor.status,
        "approved_at": vendor.approved_at.isoformat() if vendor.approved_at else None,
        "rating": float(vendor.rating) if vendor.rating is not None else 0.0,
        "review_count": vendor.review_count,
        "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
    }


def _auth_session_user_payload(user: CoreUser) -> dict:
    """
    User object for OTP confirmation and login: base fields, account_type, vendor/customer blocks.
    Vendor person name: `core_users.first_name` / `last_name`; business: `vendors` row.
    """
    base = _user_payload(user)
    account_type = _account_type_from_role(user)
    payload: dict = {
        **base,
        "account_type": account_type,
    }
    role_name = (user.role.name if user.role else "") or ""
    upper = role_name.upper()
    if upper == "VENDOR":
        payload["vendor_person_name"] = (user.first_name or "").strip()
        vendor = getattr(user, "vendor", None)
        if vendor is not None:
            payload["vendor"] = _vendor_business_payload(vendor)
        else:
            payload["vendor"] = None
        payload["customer"] = None
        payload["admin"] = None
    elif upper in {"ADMIN", "SUPER_ADMIN"} or getattr(user, "is_superuser", False):
        payload["vendor"] = None
        payload["customer"] = None
        payload["admin"] = {
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }
    else:
        payload["vendor"] = None
        payload["customer"] = {
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        payload["admin"] = None
    return payload


def _user_status_label(user: CoreUser) -> str:
    if getattr(user, "status_ref", None):
        return user.status_ref.name
    return "active" if user.is_active else "suspended"


def _my_profile_core(user: CoreUser) -> dict:
    """Core user fields for my-profile (includes media and account status label)."""
    base = _user_payload(user)
    base["avatar_url"] = user.avatar_url
    base["cover_url"] = user.cover_url
    base["bio"] = user.bio
    base["status"] = _user_status_label(user)
    return base


def _my_profile_payload(user: CoreUser) -> dict:
    """
    Full profile for GET /api/auth/my-profile and /api/admin/my-profile (any authenticated role).
    """
    core = _my_profile_core(user)
    account_type = _account_type_from_role(user)
    payload: dict = {
        **core,
        "account_type": account_type,
    }
    role_name = (user.role.name if user.role else "") or ""
    upper = role_name.upper()
    if upper == "VENDOR":
        payload["vendor_person_name"] = (user.first_name or "").strip()
        vendor = getattr(user, "vendor", None)
        if vendor is not None:
            payload["vendor"] = _vendor_business_payload(vendor)
        else:
            payload["vendor"] = None
        payload["customer"] = None
        payload["admin"] = None
    elif upper in {"ADMIN", "SUPER_ADMIN"} or getattr(user, "is_superuser", False):
        payload["vendor"] = None
        payload["customer"] = None
        payload["admin"] = {
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }
    else:
        payload["vendor"] = None
        payload["customer"] = {
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        payload["admin"] = None
    return payload


def apply_self_profile_patch(user: CoreUser, data: dict) -> tuple[list[str], dict | None]:
    """
    Validates and applies self-service profile fields on `user` (in-place).
    Returns (update_fields, validation_errors) — errors is None if OK.
    """
    errors = ValidatorService.validate(
        data,
        rules={
            "first_name": "nullable",
            "last_name": "nullable",
            "phone": "nullable",
            "email": "nullable|email",
            "avatar_url": "nullable",
            "cover_url": "nullable",
            "bio": "nullable",
        },
        custom_messages={
            "email.email": "Email must be a valid address.",
        },
    )
    if errors:
        return [], errors

    update_fields: list[str] = []

    for field in ["first_name", "last_name", "bio"]:
        if field in data:
            setattr(user, field, data.get(field))
            update_fields.append(field)

    for field in ["avatar_url", "cover_url"]:
        if field in data:
            raw = data.get(field)
            val = (raw or "").strip() or None if isinstance(raw, str) else raw
            setattr(user, field, val)
            update_fields.append(field)

    if "phone" in data:
        phone = (data.get("phone") or "").strip() or None
        if phone and CoreUser.objects.exclude(pk=user.pk).filter(phone=phone).exists():
            return [], {"phone": ["Phone already registered."]}
        user.phone = phone
        update_fields.append("phone")

    if "email" in data:
        raw_email = data.get("email")
        email = (raw_email or "").strip() or None
        if email:
            email = CoreUser.objects.normalize_email(email)
            if CoreUser.objects.exclude(pk=user.pk).filter(email=email).exists():
                return [], {"email": ["Email already registered."]}
        user.email = email
        update_fields.append("email")

    return update_fields, None


def _upload_error_response(exc: Exception) -> Response | None:
    if isinstance(exc, SupabaseNotConfiguredError):
        return ResponseService.response(
            "INTERNAL_SERVER_ERROR",
            {"detail": str(exc)},
            "Storage is not configured.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if isinstance(exc, MediaValidationError):
        return ResponseService.response(
            "VALIDATION_ERROR",
            {"file": [str(exc)]},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )
    return None


def _profile_patch_data_dict(request: Request) -> dict:
    """Form/JSON fields for profile patch, excluding file parts."""
    raw = request.data
    skip = frozenset(
        {"profile_image", "avatar", "cover_image", "cover", "file", "upload_target"}
    )
    out: dict = {}
    try:
        for key in raw:
            if key in skip:
                continue
            val = raw.get(key)
            if isinstance(val, UploadedFile):
                continue
            out[key] = val
    except TypeError:
        out = dict(raw) if raw else {}
    return out


def _process_profile_image_uploads(request: Request, user: CoreUser) -> tuple[dict, Response | None]:
    """
    Upload optional profile/cover images from multipart and return URL fields to merge into patch data.
    File keys: profile_image or avatar, cover_image or cover; legacy: file + upload_target (avatar|cover).
    """
    uid = str(user.id)
    extra: dict = {}
    profile_file = request.FILES.get("profile_image") or request.FILES.get("avatar")
    cover_file = request.FILES.get("cover_image") or request.FILES.get("cover")
    legacy = request.FILES.get("file")
    target = (request.data.get("upload_target") or request.POST.get("upload_target") or "").strip().lower()
    if legacy and not profile_file and not cover_file:
        if target in ("cover", "cover_image"):
            cover_file = legacy
        else:
            profile_file = legacy

    for file_obj, url_field in (
        (profile_file, "avatar_url"),
        (cover_file, "cover_url"),
    ):
        if not file_obj:
            continue
        try:
            url, _ = upload_django_file("profile", uid, file_obj, allow_video=False)
            extra[url_field] = url
        except (SupabaseNotConfiguredError, MediaValidationError) as e:
            err = _upload_error_response(e)
            if err:
                return {}, err
            raise
        except Exception as e:
            return {}, ResponseService.response(
                "INTERNAL_SERVER_ERROR",
                {"detail": str(e)},
                "Upload failed.",
                status.HTTP_502_BAD_GATEWAY,
            )
    return extra, None


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
            "email": "nullable|email|unique:core_users,email",
            "phone": "required|unique:core_users,phone",
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
        logger.exception("Failed preparing registration OTP for customer: %s", exc)
        return ResponseService.response(
            "SERVER_ERROR",
            {"detail": "Registration could not be completed. Please try again."},
            "Registration failed.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    log_activity(
        actor=user,
        category="registration",
        event="customer_registered",
        resource_type="core_user",
        resource_id=user.id,
        payload={"role": "customer"},
    )

    return ResponseService.response(
        "SUCCESS",
        {
            "user": _user_payload(user),
            "otp_sent": False,
            "otp_expires_in_seconds": int(getattr(settings, "OTP_EXPIRES_IN_SECONDS", 600)),
        },
        "Customer registered successfully. Confirm with static OTP 111111.",
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
            "email": "nullable|email|unique:core_users,email",
            "phone": "required|unique:core_users,phone",
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
            approved_status, _ = CoreStatus.objects.get_or_create(
                status_type="vendor_approved",
                defaults={"entity_type": "vendor", "name": "approved", "sort_order": 20},
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
                status="approved",
                status_ref=approved_status,
            )
            _send_registration_otp(user)
    except Exception as exc:
        logger.exception("Failed preparing registration OTP for vendor: %s", exc)
        return ResponseService.response(
            "SERVER_ERROR",
            {"detail": "Registration could not be completed. Please try again."},
            "Registration failed.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    log_activity(
        actor=user,
        category="registration",
        event="vendor_registered",
        resource_type="core_user",
        resource_id=user.id,
        payload={"role": "vendor", "store_name": name},
    )

    return ResponseService.response(
        "SUCCESS",
        {
            "user": _user_payload(user),
            "otp_sent": False,
            "otp_expires_in_seconds": int(getattr(settings, "OTP_EXPIRES_IN_SECONDS", 600)),
        },
        "Vendor registered successfully. Confirm with static OTP 111111.",
        status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    data = request.data
    phone = _phone_from_registration_data(data)
    password = data.get("password") or ""

    validation_payload = _data_with_phone_for_validation(data, phone)
    errors = ValidatorService.validate(
        validation_payload,
        rules={
            "password": "required",
            "phone": "required",
        },
        custom_messages={
            "password.required": "Password is required.",
            "phone.required": "Phone is required.",
        },
    )

    if errors:
        return ResponseService.response(
            "VALIDATION_ERROR",
            errors,
            "Validation Error",
        )

    user: CoreUser | None = None
    try:
        user = CoreUser.objects.select_related("role", "vendor", "vendor__category").get(phone=phone)
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
    log_activity(
        actor=user,
        category="session",
        event="login_success",
        resource_type="core_user",
        resource_id=user.id,
    )

    return ResponseService.response(
        "SUCCESS",
        {"tokens": tokens, "user": _auth_session_user_payload(user)},
        "Login successful.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_login_view(request: Request) -> Response:
    """
    JWT login for staff dashboard clients. Password required; send email or phone.
    Public /api/auth/login uses phone + password only.
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
    log_activity(
        actor=user,
        category="session",
        event="admin_login_success",
        resource_type="core_user",
        resource_id=user.id,
    )

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
        user = CoreUser.objects.select_related("role", "vendor", "vendor__category").get(id=user_id)
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
    log_activity(
        actor=user,
        category="registration",
        event="otp_confirmed",
        resource_type="core_user",
        resource_id=user.id,
    )

    tokens = _build_tokens_for_user(user)
    return ResponseService.response(
        "SUCCESS",
        {"tokens": tokens, "user": _auth_session_user_payload(user)},
        "OTP confirmed. Registration completed successfully.",
        status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def my_profile_view(request: Request) -> Response:
    """
    Current user profile from JWT (customer, vendor, or admin).
    GET returns full core user + role-specific block (vendor / customer / admin).
    PUT/PATCH update profile: same JSON/form fields as before (first_name, last_name, phone, email,
    avatar_url, cover_url, bio) plus optional multipart files:
    profile_image or avatar, cover_image or cover (Supabase upload); legacy: file + upload_target
    (avatar|cover).
    """
    user_id = request.user.pk
    if request.method in ("PUT", "PATCH"):
        user = CoreUser.objects.get(pk=user_id)
        uploaded, upload_err = _process_profile_image_uploads(request, user)
        if upload_err:
            return upload_err
        data = _profile_patch_data_dict(request)
        data.update(uploaded)
        update_fields, errors = apply_self_profile_patch(user, data)
        if errors:
            return ResponseService.response(
                "VALIDATION_ERROR",
                errors,
                "Validation Error",
            )
        if update_fields:
            user.save(update_fields=update_fields)
        message = "Profile updated successfully."
    else:
        message = "Profile fetched successfully."

    user = CoreUser.objects.select_related("role", "status_ref", "vendor", "vendor__category").get(pk=user_id)
    return ResponseService.response(
        "SUCCESS",
        _my_profile_payload(user),
        message,
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request: Request) -> Response:
    user = request.user if isinstance(request.user, CoreUser) else None
    refresh_token = request.data.get("refresh")
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            # If blacklist is not enabled or token invalid, ignore.
            pass

    log_activity(
        actor=user,
        category="session",
        event="logout",
        resource_type="core_user" if user else None,
        resource_id=user.id if user else None,
    )

    return ResponseService.response(
        "SUCCESS",
        {},
        "Logged out successfully.",
        status.HTTP_200_OK,
    )

