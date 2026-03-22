from __future__ import annotations

import json

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

import mServices.ResponseService as ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from mServices.ValidatorService import ValidatorService

from vendly_backend.models import Vendor


def _require_vendor(request: Request) -> tuple[Vendor | None, Response | None]:
    try:
        return request.user.vendor, None  # type: ignore[attr-defined]
    except Vendor.DoesNotExist:
        return None, ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor profile not found.",
            status.HTTP_404_NOT_FOUND,
        )


def _profile_payload_from_row(row: dict) -> dict:
    rating = row.get("rating")
    price_from = row.get("price_from")
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "city": row.get("city"),
        "category_id": row.get("category_id"),
        "rating": float(rating) if rating is not None else 0.0,
        "review_count": row.get("review_count") or 0,
        "price_from": str(price_from) if price_from is not None else None,
        "bio": row.get("bio"),
        "status": row.get("status"),
    }


def get_vendor_profile(request: Request, vendor: Vendor) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 1))
        sort_by = (request.GET.get("sort_by") or "id").strip().lower()
        sort_dir = (request.GET.get("sort_dir") or "desc").strip().lower()

        sort_map = {
            "id": "vendors.id",
            "created_at": "vendors.created_at",
            "name": "vendors.name",
        }
        if sort_by not in sort_map:
            raise ValueError("Invalid sort_by")
        sort_col = sort_map[sort_by]
        if sort_dir not in ("asc", "desc"):
            raise ValueError("Invalid sort_dir")

        filters: dict[str, object] = {"id": {"o": "=", "v": vendor.id}}
        raw_filters = request.GET.get("filters")
        if raw_filters is not None and str(raw_filters).strip() != "":
            extra = json.loads(raw_filters)
            if not isinstance(extra, dict):
                raise ValueError("filters must be a JSON object")
            for key, val in extra.items():
                if key == "id":
                    continue
                if isinstance(val, dict) and "o" in val and "v" in val:
                    filters[key] = val
                else:
                    filters[key] = {"o": "=", "v": val}

        filter_json = json.dumps(filters)
        filter_keys = list(filters.keys())

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
            )
            .apply_conditions(filter_json, filter_keys, "", [])
            .paginate(page, limit, ["vendors.id", sort_col], sort_col, sort_dir)
        )

        rows = query.get("data") or []
        if not rows:
            return ResponseService.response(
                "NOT_FOUND",
                {},
                "Vendor profile not found.",
                status.HTTP_404_NOT_FOUND,
            )

        payload = _profile_payload_from_row(rows[0])
        return ResponseService.response(
            "SUCCESS",
            payload,
            "Vendor profile fetched successfully.",
            status.HTTP_200_OK,
        )
    except ValidationError as e:
        return ResponseService.response(
            "VALIDATION_ERROR",
            getattr(e, "message_dict", None) or {"detail": [str(e)]},
            "Validation Error",
            status.HTTP_400_BAD_REQUEST,
        )
    except (ValueError, json.JSONDecodeError):
        return ResponseService.response(
            "VALIDATION_ERROR",
            {"pagination": ["Invalid parameters"]},
            "Invalid Request",
            status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


def patch_vendor_profile(request: Request, vendor: Vendor) -> Response:
    try:
        data = request.data
        errors = ValidatorService.validate(
            data,
            rules={
                "name": "nullable|string|max:255",
                "city": "nullable|string|max:255",
                "bio": "nullable|string",
                "price_from": "nullable|numeric",
            },
            custom_messages={},
        )
        if errors:
            return ResponseService.response(
                "VALIDATION_ERROR",
                errors,
                "Validation Error",
                status.HTTP_400_BAD_REQUEST,
            )

        for field in ["name", "city", "bio", "price_from"]:
            if field not in data:
                continue
            if field == "price_from":
                val = data.get(field)
                if val is None or val == "":
                    setattr(vendor, field, None)
                else:
                    setattr(vendor, field, val)
            else:
                setattr(vendor, field, data.get(field))

        vendor.save()
        payload = {
            "id": vendor.id,
            "name": vendor.name,
            "city": vendor.city,
            "category_id": vendor.category_id,
            "rating": float(vendor.rating) if vendor.rating is not None else 0.0,
            "review_count": vendor.review_count,
            "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
            "bio": vendor.bio,
            "status": vendor.status,
        }
        return ResponseService.response(
            "SUCCESS",
            payload,
            "Vendor profile updated successfully.",
            status.HTTP_200_OK,
        )
    except ValidationError as e:
        return ResponseService.response(
            "VALIDATION_ERROR",
            getattr(e, "message_dict", None) or {"detail": [str(e)]},
            "Validation Error",
            status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def vendor_profile_view(request: Request) -> Response:
    vendor, err = _require_vendor(request)
    if err is not None:
        return err
    if request.method == "GET":
        return get_vendor_profile(request, vendor)
    return patch_vendor_profile(request, vendor)
