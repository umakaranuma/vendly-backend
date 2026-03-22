from __future__ import annotations

import json

import mServices.ResponseService as ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from mServices.ValidatorService import ValidatorService
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from vendly_backend.controllers.auth_controller import apply_self_profile_patch, _my_profile_payload
from vendly_backend.models import CoreRole, CoreStatus, CoreUser, Vendor


def _get_status_ref(entity_type: str, status_type: str, name: str):
    """
    Returns a CoreStatus row, seeding it if missing.
    """
    status_ref, _ = CoreStatus.objects.get_or_create(
        status_type=status_type,
        defaults={"entity_type": entity_type, "name": name, "sort_order": 10},
    )
    return status_ref


def _serialize_user(user: CoreUser) -> dict:
    role = user.role
    role_payload = None
    if role:
        role_payload = {"id": role.id, "name": role.name, "description": role.description}

    user_status = (
        user.status_ref.name
        if getattr(user, "status_ref", None)
        else ("active" if user.is_active else "suspended")
    )

    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": user.avatar_url,
        "cover_url": user.cover_url,
        "bio": user.bio,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "status": user_status,
        "role": role_payload,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_users(request: Request) -> Response:
    return _list_users_response(request)


def _list_users_response(request: Request, forced_user_id: int | None = None) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        role_name = (request.GET.get("role") or "").strip()
        status_key = (request.GET.get("status") or "").strip().lower()  # active | suspended | pending
        search_string = request.GET.get("search", "")

        filters: dict[str, object] = {}
        if role_name:
            filters["core_roles.name"] = role_name
        if forced_user_id is not None:
            filters["core_users.id"] = forced_user_id
        if status_key == "active":
            filters["core_users.is_active"] = True
        elif status_key == "suspended":
            filters["core_users.is_active"] = False
        elif status_key == "pending":
            filters["core_users.is_active"] = True
            filters["core_users.is_verified"] = False
        filter_json = json.dumps(filters)

        query = (
            QueryBuilderService("core_users")
            .select(
                "core_users.id",
                "core_users.email",
                "core_users.phone",
                "core_users.first_name",
                "core_users.last_name",
                "core_users.is_active",
                "core_users.is_verified",
                "core_roles.id as role_id",
                "core_roles.name as role_name",
                "core_roles.description as role_description",
                "core_statuses.name as status",
            )
            .leftJoin("core_roles", "core_roles.id", "core_users.role_id")
            .leftJoin("core_statuses", "core_statuses.id", "core_users.status_id")
            .apply_conditions(
                filter_json,
                ["core_roles.name", "core_users.id", "core_users.is_active", "core_users.is_verified"],
                search_string,
                ["core_users.first_name", "core_users.last_name", "core_users.email", "core_users.phone"],
            )
            .paginate(page, limit, ["core_users.id", "core_users.created_at"], "core_users.created_at", "desc")
        )
        return ResponseService.response(
            "SUCCESS",
            query,
            "Users fetched successfully.",
            status.HTTP_200_OK,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
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

    data = _serialize_user(user)

    return ResponseService.response(
        "SUCCESS",
        data,
        "User fetched successfully.",
        status.HTTP_200_OK,
    )


def _resolve_users_target_id(path_user_id: int | None, request: Request) -> tuple[int | None, Response | None]:
    """
    Returns (target_id, error_response).
    If both path id and `?id=` are present, they must match.
    """
    raw = request.GET.get("id")
    if path_user_id is not None:
        if raw is not None and str(raw).strip() != "":
            try:
                q = int(raw)
            except (TypeError, ValueError):
                return None, ResponseService.response(
                    "VALIDATION_ERROR",
                    {"id": ["Invalid id."]},
                    "Validation Error",
                    status.HTTP_400_BAD_REQUEST,
                )
            if q != path_user_id:
                return None, ResponseService.response(
                    "VALIDATION_ERROR",
                    {"id": ["Query id must match path id."]},
                    "Validation Error",
                    status.HTTP_400_BAD_REQUEST,
                )
        return path_user_id, None
    if raw is not None and str(raw).strip() != "":
        try:
            return int(raw), None
        except (TypeError, ValueError):
            return None, ResponseService.response(
                "VALIDATION_ERROR",
                {"id": ["Invalid id."]},
                "Validation Error",
                status.HTTP_400_BAD_REQUEST,
            )
    return None, None


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def users_view(request: Request, path_user_id: int | None = None) -> Response:
    """
    Unified user endpoint (any authenticated user):
    - `GET /api/users` lists users (paginated query builder).
    - `GET /api/users/<id>` or `?id=` fetches one user (full profile payload).
    - `PATCH /api/users`, `PATCH /api/users/<id>`, or `?id=` updates that user (same fields as my-profile).
    Admin bulk role/status updates remain on `/api/admin/users/<user_id>/update`.
    """

    resolved_id, resolve_err = _resolve_users_target_id(path_user_id, request)
    if resolve_err is not None:
        return resolve_err

    query_id_raw = request.GET.get("id")
    user_id = str(resolved_id) if resolved_id is not None else query_id_raw

    if request.method == "PATCH":
        if user_id:
            try:
                target_id = int(user_id)
            except (TypeError, ValueError):
                return ResponseService.response(
                    "VALIDATION_ERROR",
                    {"id": ["Invalid id."]},
                    "Validation Error",
                    status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_id = request.user.id

        try:
            target_user = CoreUser.objects.get(pk=target_id)
        except CoreUser.DoesNotExist:
            return ResponseService.response(
                "NOT_FOUND",
                {},
                "User not found.",
                status.HTTP_404_NOT_FOUND,
            )

        data = request.data
        update_fields, errors = apply_self_profile_patch(target_user, data)
        if errors:
            return ResponseService.response(
                "VALIDATION_ERROR",
                errors,
                "Validation Error",
                status.HTTP_400_BAD_REQUEST,
            )
        if update_fields:
            target_user.save(update_fields=update_fields)

        target_user = CoreUser.objects.select_related("role", "status_ref", "vendor", "vendor__category").get(
            pk=target_id
        )
        return ResponseService.response(
            "SUCCESS",
            _my_profile_payload(target_user),
            "Profile updated successfully.",
            status.HTTP_200_OK,
        )

    if user_id:
        try:
            target_id = int(user_id)
        except (TypeError, ValueError):
            return ResponseService.response(
                "VALIDATION_ERROR",
                {"id": ["Invalid id."]},
                "Validation Error",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_user = CoreUser.objects.select_related("role", "status_ref", "vendor", "vendor__category").get(
                pk=target_id
            )
        except CoreUser.DoesNotExist:
            return ResponseService.response(
                "NOT_FOUND",
                {},
                "User not found.",
                status.HTTP_404_NOT_FOUND,
            )

        return ResponseService.response(
            "SUCCESS",
            _my_profile_payload(target_user),
            "User fetched successfully.",
            status.HTTP_200_OK,
        )

    # No `id` provided — list users (same filters as admin user list).
    return _list_users_response(request)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
def list_vendors(request: Request) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        status_key = (request.GET.get("status") or "").strip().lower()  # all | active | pending | inactive | suspended
        search_string = request.GET.get("search", "")

        filters: dict[str, object] = {}
        if status_key == "active":
            filters["vendors.status"] = "approved"
        elif status_key == "pending":
            filters["vendors.status"] = "pending"
        elif status_key == "inactive":
            filters["vendors.status"] = "rejected"
        elif status_key == "suspended":
            filters["vendors.status"] = "suspended"
        filter_json = json.dumps(filters)

        query = (
            QueryBuilderService("vendors")
            .select(
                "vendors.id",
                "vendors.name",
                "vendors.city",
                "vendors.category_id",
                "vendors.rating",
                "vendors.review_count",
                "vendors.price_from",
                "vendors.bio",
                "vendors.status",
                "core_statuses.name as status_ref_name",
            )
            .leftJoin("core_statuses", "core_statuses.id", "vendors.status_id")
            .apply_conditions(
                filter_json,
                ["vendors.status"],
                search_string,
                ["vendors.name", "vendors.city", "vendors.bio"],
            )
            .paginate(page, limit, ["vendors.id", "vendors.created_at"], "vendors.created_at", "desc")
        )
        return ResponseService.response(
            "SUCCESS",
            query,
            "Vendors fetched successfully.",
            status.HTTP_200_OK,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
def resume_vendor(request: Request, vendor_id: int) -> Response:
    # Resume from suspension -> treat as approved/active.
    return approve_vendor(request, vendor_id)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
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

