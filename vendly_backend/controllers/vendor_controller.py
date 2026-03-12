from __future__ import annotations

import mServices.ResponseService as ResponseService
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from vendly_backend.models import VendorProfile
from vendly_backend.permissions import IsVendor


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsVendor])
def vendor_profile_view(request: Request) -> Response:
    user = request.user
    try:
        profile = user.vendor_profile  # type: ignore[attr-defined]
    except VendorProfile.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor profile not found.",
            status.HTTP_404_NOT_FOUND,
        )

    if request.method == "PATCH":
        data = request.data
        # Allow updating a subset of profile fields
        for field in [
            "store_name",
            "business_name",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "contact_email",
            "contact_phone",
        ]:
            if field in data:
                setattr(profile, field, data.get(field))
        profile.save()
        message = "Vendor profile updated successfully."
    else:
        message = "Vendor profile fetched successfully."

    payload = {
        "id": profile.id,
        "store_name": profile.store_name,
        "business_name": profile.business_name,
        "address": profile.address,
        "city": profile.city,
        "state": profile.state,
        "country": profile.country,
        "postal_code": profile.postal_code,
        "latitude": str(profile.latitude) if profile.latitude is not None else None,
        "longitude": str(profile.longitude) if profile.longitude is not None else None,
        "contact_email": profile.contact_email,
        "contact_phone": profile.contact_phone,
        "is_approved": profile.is_approved,
        "is_blocked": profile.is_blocked,
        "rejection_reason": profile.rejection_reason,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        message,
        status.HTTP_200_OK,
    )

