from __future__ import annotations

import json

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

import mServices.ResponseService as ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from mServices.ValidatorService import ValidatorService

from vendly_backend.models import Vendor, VendorFollower, VendorReport, VendorProfile
from vendly_backend.permissions import is_admin_user
from vendly_backend.vendor_ratings import public_vendor_rating_and_count


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


def _public_vendor_status_display(vendor: Vendor) -> str:
    if getattr(vendor, "status_ref", None):
        return vendor.status_ref.name
    if vendor.status == "approved":
        return "active"
    return vendor.status


def _public_vendor_payload(vendor: Vendor, request=None) -> dict:
    """Vendor row plus linked user profile (avatar, cover, names) for public API responses."""
    u = vendor.user
    cat = vendor.category
    rating, review_count = public_vendor_rating_and_count(vendor)

    # Determine if the requesting user follows this vendor
    is_followed_by_me = False
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        is_followed_by_me = VendorFollower.objects.filter(
            vendor=vendor, user=request.user
        ).exists()

    return {
        "id": vendor.id,
        "name": vendor.name,
        "slug": vendor.slug,
        "city": vendor.city,
        "address": getattr(u.profile, "address", "") if hasattr(u, "profile") else "",
        "latitude": (
            float(u.profile.latitude)
            if hasattr(u, "profile") and u.profile.latitude is not None
            else None
        ),
        "longitude": (
            float(u.profile.longitude)
            if hasattr(u, "profile") and u.profile.longitude is not None
            else None
        ),
        "category_id": vendor.category_id,
        "category": (
            {"id": cat.id, "name": cat.name, "slug": cat.slug, "cover_image_url": cat.cover_image_url}
            if cat
            else None
        ),
        "rating": rating,
        "review_count": review_count,
        "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
        "bio": vendor.bio,
        "status": _public_vendor_status_display(vendor),
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "followers_count": vendor.followers_count if hasattr(vendor, 'followers_count') else 0,
        "following_count": VendorFollower.objects.filter(user=vendor.user).count(),
        "is_followed_by_me": is_followed_by_me,
        "user": {
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "avatar_url": u.avatar_url,
            "cover_url": u.cover_url,
            "bio": u.bio,
        },
    }


def list_public_vendors(request: Request) -> Response:
    """Paginated list of approved vendors (public).

    Optional query params: category_id (filter); search or q (name, category name, category slug).
    """
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        if page < 1 or limit < 1:
            raise ValueError("Invalid pagination")

        qs = (
            Vendor.objects.filter(status="approved")
            .select_related("user", "category", "status_ref")
            .annotate(
                _reviews_count=Count("reviews"),
                _reviews_avg=Avg("reviews__rating"),
            )
            .order_by("-created_at")
        )

        raw_category_id = request.GET.get("category_id")
        if raw_category_id is not None and str(raw_category_id).strip() != "":
            qs = qs.filter(category_id=int(raw_category_id))

        search_term = (request.GET.get("search") or request.GET.get("q") or "").strip()
        if search_term:
            qs = qs.filter(
                Q(name__icontains=search_term)
                | Q(category__name__icontains=search_term)
                | Q(category__slug__icontains=search_term)
            )
        paginator = Paginator(qs, limit)
        page_obj = paginator.get_page(page)
        data = [_public_vendor_payload(v, request) for v in page_obj.object_list]
        result = {
            "total_records": paginator.count,
            "per_page": limit,
            "current_page": page_obj.number,
            "last_page": paginator.num_pages or 1,
            "data": data,
        }
        return ResponseService.response(
            "SUCCESS",
            result,
            "Vendors fetched successfully.",
            status.HTTP_200_OK,
        )
    except (ValueError, ValidationError):
        return ResponseService.response(
            "VALIDATION_ERROR",
            {"pagination": ["Invalid parameters"]},
            "Invalid Request",
            status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


def retrieve_public_vendor(request: Request, vendor_id: int) -> Response:
    """Single approved vendor (public)."""
    try:
        vendor = (
            Vendor.objects.filter(status="approved", pk=vendor_id)
            .select_related("user", "category", "status_ref")
            .annotate(
                _reviews_count=Count("reviews"),
                _reviews_avg=Avg("reviews__rating"),
            )
            .first()
        )
        if vendor is None:
            return ResponseService.response(
                "NOT_FOUND",
                {},
                "Vendor not found.",
                status.HTTP_404_NOT_FOUND,
            )
        return ResponseService.response(
            "SUCCESS",
            _public_vendor_payload(vendor, request),
            "Vendor fetched successfully.",
            status.HTTP_200_OK,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


def delete_vendor_as_admin(request: Request, vendor_id: int) -> Response:
    """Remove vendor profile; admin only. Linked user account remains (use admin user tools to suspend)."""
    if not request.user.is_authenticated:
        return ResponseService.response(
            "UNAUTHORIZED",
            {"detail": "Authentication required."},
            "Authentication required.",
            status.HTTP_401_UNAUTHORIZED,
        )
    if not is_admin_user(request.user):
        return ResponseService.response(
            "FORBIDDEN",
            {"detail": "Only administrators can delete a vendor."},
            "Forbidden",
            status.HTTP_403_FORBIDDEN,
        )
    try:
        vendor = Vendor.objects.select_related("user").get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )
    try:
        vendor.delete()
        return ResponseService.response("SUCCESS", {}, "Vendor deleted.", status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


@api_view(["GET"])
@permission_classes([AllowAny])
def public_vendors_list_view(request: Request) -> Response:
    return list_public_vendors(request)


@api_view(["GET", "DELETE"])
@permission_classes([AllowAny])
def public_vendor_detail_view(request: Request, vendor_id: int) -> Response:
    if request.method == "GET":
        return retrieve_public_vendor(request, vendor_id)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report_vendor_view(request: Request, vendor_id: int) -> Response:
    """Report a vendor for spam, inappropriate content, etc."""
    try:
        vendor = Vendor.objects.get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Vendor not found.",
            status.HTTP_404_NOT_FOUND,
        )

    data = request.data
    errors = ValidatorService.validate(
        data,
        rules={
            "reason": "required|string|max:255",
            "details": "nullable|string",
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

    report = VendorReport.objects.create(
        vendor=vendor,
        reporter=request.user,
        reason=data.get("reason"),
        details=data.get("details"),
    )

    return ResponseService.response(
        "SUCCESS",
        {"id": report.id},
        "Report submitted successfully. Thank you for helping keep our community safe.",
        status.HTTP_201_CREATED,
    )
