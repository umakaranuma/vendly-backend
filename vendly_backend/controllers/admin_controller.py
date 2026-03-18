from __future__ import annotations

import mServices.ResponseService as ResponseService
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from vendly_backend.models import CoreRole, CoreStatus, CoreUser, Vendor
from vendly_backend.permissions import IsAdmin


def _get_status_ref(entity_type: str, status_type: str, name: str):
    """
    Returns a CoreStatus row, seeding it if missing.
    """
    status_ref, _ = CoreStatus.objects.get_or_create(
        status_type=status_type,
        defaults={"entity_type": entity_type, "name": name, "sort_order": 10},
    )
    return status_ref


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def list_users(request: Request) -> Response:
    role_name = request.GET.get("role")
    status_key = request.GET.get("status")  # active | suspended | pending (optional)
    users = CoreUser.objects.all().select_related("role")
    if role_name:
        users = users.filter(role__name__iexact=role_name)

    if status_key:
        if status_key == "active":
            users = users.filter(is_active=True)
        elif status_key == "suspended":
            users = users.filter(is_active=False)
        elif status_key == "pending":
            # Pending definition for customers is not explicitly used in your flow.
            users = users.filter(is_active=True, is_verified=False)

    data = []
    for user in users:
        role = user.role
        role_payload = None
        if role:
            role_payload = {"id": role.id, "name": role.name, "description": role.description}
        user_status = (
            user.status_ref.name if getattr(user, "status_ref", None) else ("active" if user.is_active else "suspended")
        )
        data.append(
            {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "status": user_status,
                "role": role_payload,
            }
        )

    return ResponseService.response(
        "SUCCESS",
        data,
        "Users fetched successfully.",
        status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def retrieve_user(request: Request, user_id: int) -> Response:
    try:
        user = CoreUser.objects.select_related("role").get(pk=user_id)
    except CoreUser.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "User not found.",
            status.HTTP_404_NOT_FOUND,
        )

    role = user.role
    role_payload = None
    if role:
        role_payload = {"id": role.id, "name": role.name, "description": role.description}

    data = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "status": user.status_ref.name if getattr(user, "status_ref", None) else ("active" if user.is_active else "suspended"),
        "role": role_payload,
    }

    return ResponseService.response(
        "SUCCESS",
        data,
        "User fetched successfully.",
        status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdmin])
def update_user(request: Request, user_id: int) -> Response:
    try:
        user = CoreUser.objects.get(pk=user_id)
    except CoreUser.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "User not found.",
            status.HTTP_404_NOT_FOUND,
        )

    data = request.data
    role_name = data.get("role_name")

    # Allow admin to update a subset of fields
    for field in ["first_name", "last_name", "email", "phone", "is_active", "is_verified"]:
        if field in data:
            setattr(user, field, data.get(field))

    # Keep status_ref synced with is_active (best-effort; if data doesn't include is_active, keep as-is).
    if "is_active" in data:
        if user.is_active:
            user.status_ref = _get_status_ref("customer", "customer_active", "active")
        else:
            user.status_ref = _get_status_ref("customer", "customer_suspended", "suspended")

    if role_name:
        role, _ = CoreRole.objects.get_or_create(name=role_name)
        user.role = role
    user.save()

    role = user.role
    role_payload = None
    if role:
        role_payload = {"id": role.id, "name": role.name, "description": role.description}

    payload = {
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
        payload,
        "User updated successfully.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def block_user(request: Request, user_id: int) -> Response:
    try:
        user = CoreUser.objects.get(pk=user_id)
    except CoreUser.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "User not found.",
            status.HTTP_404_NOT_FOUND,
        )

    user.is_active = False
    user.status_ref = _get_status_ref("customer", "customer_suspended", "suspended")
    user.save(update_fields=["is_active", "status_ref"])

    payload = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        "User blocked successfully.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def unblock_user(request: Request, user_id: int) -> Response:
    try:
        user = CoreUser.objects.get(pk=user_id)
    except CoreUser.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "User not found.",
            status.HTTP_404_NOT_FOUND,
        )

    user.is_active = True
    user.status_ref = _get_status_ref("customer", "customer_active", "active")
    user.save(update_fields=["is_active", "status_ref"])

    payload = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        "User unblocked successfully.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def change_user_status(request: Request) -> Response:
    """
    Single endpoint for admin to change user status.

    Body:
    - user_id: int (required)
    - status: "block" | "unblock" | "suspend" | "resume" (required)
    """
    user_id = request.data.get("user_id")
    action = (request.data.get("status") or "").strip().lower()

    valid_actions = {"block", "unblock", "suspend", "resume"}
    if not user_id or not action or action not in valid_actions:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Provide `user_id` and valid `status` (block|unblock|suspend|resume)."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = CoreUser.objects.get(pk=int(user_id))
    except (CoreUser.DoesNotExist, ValueError, TypeError):
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "User not found.",
            status.HTTP_404_NOT_FOUND,
        )

    if action in {"block", "suspend"}:
        user.is_active = False
        user.status_ref = _get_status_ref("customer", "customer_suspended", "suspended")
    elif action in {"unblock", "resume"}:
        user.is_active = True
        user.status_ref = _get_status_ref("customer", "customer_active", "active")

    user.save(update_fields=["is_active", "status_ref"])

    payload = {
        "id": user.id,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "status": user.status_ref.name if user.status_ref else ("active" if user.is_active else "suspended"),
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        "User status updated successfully.",
        status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def list_vendors(request: Request) -> Response:
    status_key = request.GET.get("status")  # all | active | pending | inactive | suspended
    vendors = Vendor.objects.select_related("user", "user__role", "status_ref")

    if status_key:
        if status_key == "active":
            vendors = vendors.filter(status="approved")
        elif status_key == "pending":
            vendors = vendors.filter(status="pending")
        elif status_key == "inactive":
            vendors = vendors.filter(status="rejected")
        elif status_key == "suspended":
            vendors = vendors.filter(status="suspended")

    data = []
    for v in vendors:
        if getattr(v, "status_ref", None):
            status_value = v.status_ref.name
        else:
            # Backward compatible mapping for existing rows without `status_ref` populated.
            status_value = (
                "active"
                if v.status == "approved"
                else v.status
            )
        data.append(
            {
                "id": v.id,
                "name": v.name,
                "city": v.city,
                "category_id": v.category_id,
                "rating": float(v.rating) if v.rating is not None else 0.0,
                "review_count": v.review_count,
                "price_from": str(v.price_from) if v.price_from is not None else None,
                "bio": v.bio,
                "status": status_value,
            }
        )

    return ResponseService.response(
        "SUCCESS",
        data,
        "Vendors fetched successfully.",
        status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def retrieve_vendor(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.select_related("user", "user__role", "status_ref").get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    data = {
        "id": vendor.id,
        "name": vendor.name,
        "city": vendor.city,
        "category_id": vendor.category_id,
        "rating": float(vendor.rating) if vendor.rating is not None else 0.0,
        "review_count": vendor.review_count,
        "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
        "bio": vendor.bio,
        "status": (
            vendor.status_ref.name
            if getattr(vendor, "status_ref", None)
            else ("active" if vendor.status == "approved" else vendor.status)
        ),
    }

    return ResponseService.response(
        "SUCCESS",
        data,
        "Vendor fetched successfully.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def approve_vendor(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    active_ref = _get_status_ref("vendor", "vendor_active", "active")
    vendor.status = "approved"
    vendor.status_ref = active_ref
    vendor.save(update_fields=["status", "status_ref"])

    data = {
        "id": vendor.id,
        "name": vendor.name,
        "city": vendor.city,
        "category_id": vendor.category_id,
        "rating": float(vendor.rating) if vendor.rating is not None else 0.0,
        "review_count": vendor.review_count,
        "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
        "bio": vendor.bio,
        "status": (
            vendor.status_ref.name
            if getattr(vendor, "status_ref", None)
            else ("active" if vendor.status == "approved" else vendor.status)
        ),
    }

    return ResponseService.response(
        "SUCCESS",
        data,
        "Vendor approved successfully.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def reject_vendor(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    # Note: reason is not stored if there is no rejection_reason column in new Vendor.
    rejected_ref = _get_status_ref("vendor", "vendor_rejected", "rejected")
    vendor.status = "rejected"
    vendor.status_ref = rejected_ref
    vendor.save(update_fields=["status", "status_ref"])

    data = {
        "id": vendor.id,
        "name": vendor.name,
        "city": vendor.city,
        "category_id": vendor.category_id,
        "rating": float(vendor.rating) if vendor.rating is not None else 0.0,
        "review_count": vendor.review_count,
        "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
        "bio": vendor.bio,
        "status": (
            vendor.status_ref.name
            if getattr(vendor, "status_ref", None)
            else ("active" if vendor.status == "approved" else vendor.status)
        ),
    }

    return ResponseService.response(
        "SUCCESS",
        data,
        "Vendor rejected successfully.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def suspend_vendor(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.select_related("status_ref").get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    suspended_ref = _get_status_ref("vendor", "vendor_suspended", "suspended")
    vendor.status = "suspended"
    vendor.status_ref = suspended_ref
    vendor.save(update_fields=["status", "status_ref"])

    payload = {
        "id": vendor.id,
        "name": vendor.name,
        "city": vendor.city,
        "category_id": vendor.category_id,
        "rating": float(vendor.rating) if vendor.rating is not None else 0.0,
        "review_count": vendor.review_count,
        "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
        "bio": vendor.bio,
        "status": vendor.status_ref.name if getattr(vendor, "status_ref", None) else vendor.status,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        "Vendor suspended successfully.",
        status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def resume_vendor(request: Request, vendor_id: int) -> Response:
    # Resume from suspension -> treat as approved/active.
    return approve_vendor(request, vendor_id)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def change_vendor_status(request: Request) -> Response:
    """
    Single endpoint for admin to change vendor status.

    Body:
    - vendor_id: int (required)
    - status: "approve" | "reject" | "suspend" | "resume" (required)
    """
    vendor_id = request.data.get("vendor_id")
    action = (request.data.get("status") or "").strip().lower()

    valid_actions = {"approve", "reject", "suspend", "resume"}
    if not vendor_id or not action or action not in valid_actions:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Provide `vendor_id` and valid `status` (approve|reject|suspend|resume)."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        vendor = Vendor.objects.select_related("status_ref").get(pk=int(vendor_id))
    except (Vendor.DoesNotExist, ValueError, TypeError):
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    if action in {"approve", "resume"}:
        active_ref = _get_status_ref("vendor", "vendor_active", "active")
        vendor.status = "approved"
        vendor.status_ref = active_ref
    elif action == "reject":
        rejected_ref = _get_status_ref("vendor", "vendor_rejected", "rejected")
        vendor.status = "rejected"
        vendor.status_ref = rejected_ref
    elif action == "suspend":
        suspended_ref = _get_status_ref("vendor", "vendor_suspended", "suspended")
        vendor.status = "suspended"
        vendor.status_ref = suspended_ref

    vendor.save(update_fields=["status", "status_ref"])

    return ResponseService.response(
        "SUCCESS",
        {
            "id": vendor.id,
            "status": vendor.status_ref.name if vendor.status_ref else vendor.status,
        },
        "Vendor status updated successfully.",
        status.HTTP_200_OK,
    )

