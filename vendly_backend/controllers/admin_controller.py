from __future__ import annotations

import mServices.ResponseService as ResponseService
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from vendly_backend.models import CoreRole, CoreUser, VendorProfile
from vendly_backend.permissions import IsAdmin


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def list_users(request: Request) -> Response:
    role_name = request.GET.get("role")
    users = CoreUser.objects.all().select_related("role")
    if role_name:
        users = users.filter(role__name__iexact=role_name)

    data = []
    for user in users:
        role = user.role
        role_payload = None
        if role:
            role_payload = {"id": role.id, "name": role.name, "description": role.description}
        data.append(
            {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
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
    user.save(update_fields=["is_active"])

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
    user.save(update_fields=["is_active"])

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


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def list_vendors(request: Request) -> Response:
    vendors = VendorProfile.objects.select_related("user", "user__role")
    data = []
    for v in vendors:
        data.append(
            {
                "id": v.id,
                "store_name": v.store_name,
                "business_name": v.business_name,
                "address": v.address,
                "city": v.city,
                "state": v.state,
                "country": v.country,
                "postal_code": v.postal_code,
                "latitude": str(v.latitude) if v.latitude is not None else None,
                "longitude": str(v.longitude) if v.longitude is not None else None,
                "contact_email": v.contact_email,
                "contact_phone": v.contact_phone,
                "is_approved": v.is_approved,
                "is_blocked": v.is_blocked,
                "rejection_reason": v.rejection_reason,
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
        vendor = VendorProfile.objects.select_related("user", "user__role").get(pk=vendor_id)
    except VendorProfile.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    data = {
        "id": vendor.id,
        "store_name": vendor.store_name,
        "business_name": vendor.business_name,
        "address": vendor.address,
        "city": vendor.city,
        "state": vendor.state,
        "country": vendor.country,
        "postal_code": vendor.postal_code,
        "latitude": str(vendor.latitude) if vendor.latitude is not None else None,
        "longitude": str(vendor.longitude) if vendor.longitude is not None else None,
        "contact_email": vendor.contact_email,
        "contact_phone": vendor.contact_phone,
        "is_approved": vendor.is_approved,
        "is_blocked": vendor.is_blocked,
        "rejection_reason": vendor.rejection_reason,
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
        vendor = VendorProfile.objects.get(pk=vendor_id)
    except VendorProfile.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    vendor.is_approved = True
    vendor.is_blocked = False
    vendor.rejection_reason = ""
    vendor.save(update_fields=["is_approved", "is_blocked", "rejection_reason"])

    data = {
        "id": vendor.id,
        "store_name": vendor.store_name,
        "business_name": vendor.business_name,
        "address": vendor.address,
        "city": vendor.city,
        "state": vendor.state,
        "country": vendor.country,
        "postal_code": vendor.postal_code,
        "latitude": str(vendor.latitude) if vendor.latitude is not None else None,
        "longitude": str(vendor.longitude) if vendor.longitude is not None else None,
        "contact_email": vendor.contact_email,
        "contact_phone": vendor.contact_phone,
        "is_approved": vendor.is_approved,
        "is_blocked": vendor.is_blocked,
        "rejection_reason": vendor.rejection_reason,
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
        vendor = VendorProfile.objects.get(pk=vendor_id)
    except VendorProfile.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    reason = request.data.get("reason", "")
    vendor.is_approved = False
    vendor.is_blocked = True
    vendor.rejection_reason = reason
    vendor.save(update_fields=["is_approved", "is_blocked", "rejection_reason"])

    data = {
        "id": vendor.id,
        "store_name": vendor.store_name,
        "business_name": vendor.business_name,
        "address": vendor.address,
        "city": vendor.city,
        "state": vendor.state,
        "country": vendor.country,
        "postal_code": vendor.postal_code,
        "latitude": str(vendor.latitude) if vendor.latitude is not None else None,
        "longitude": str(vendor.longitude) if vendor.longitude is not None else None,
        "contact_email": vendor.contact_email,
        "contact_phone": vendor.contact_phone,
        "is_approved": vendor.is_approved,
        "is_blocked": vendor.is_blocked,
        "rejection_reason": vendor.rejection_reason,
    }

    return ResponseService.response(
        "SUCCESS",
        data,
        "Vendor rejected successfully.",
        status.HTTP_200_OK,
    )

