from __future__ import annotations

import mServices.ResponseService as ResponseService
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from vendly_backend.models import Vendor


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def vendor_profile_view(request: Request) -> Response:
    user = request.user
    try:
        profile = user.vendor  # type: ignore[attr-defined]
    except Vendor.DoesNotExist:
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
            "name",
            "city",
            "bio",
            "price_from",
        ]:
            if field in data:
                setattr(profile, field, data.get(field))
        profile.save()
        message = "Vendor profile updated successfully."
    else:
        message = "Vendor profile fetched successfully."

    payload = {
        "id": profile.id,
        "name": profile.name,
        "city": profile.city,
        "category_id": profile.category_id,
        "rating": float(profile.rating) if profile.rating is not None else 0.0,
        "review_count": profile.review_count,
        "price_from": str(profile.price_from) if profile.price_from is not None else None,
        "bio": profile.bio,
        "status": profile.status,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        message,
        status.HTTP_200_OK,
    )

