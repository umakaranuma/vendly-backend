from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from vendly_backend.models import Booking, Category, CoreUser, Vendor, VendorSubscription
def _last_month_range():
    now = timezone.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_day_this_month
    last_month_start = (first_day_this_month - timedelta(days=1)).replace(day=1)
    return last_month_start, last_month_end


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard_summary_view(request: Request) -> Response:
    last_month_start, last_month_end = _last_month_range()

    total_users = CoreUser.objects.count()
    total_vendors = Vendor.objects.count()

    new_users_last_month = CoreUser.objects.filter(
        created_at__gte=last_month_start, created_at__lt=last_month_end
    ).count()

    earnings_last_month = (
        Booking.objects.filter(
            status__name="completed",
            booking_date__gte=last_month_start,
            booking_date__lt=last_month_end,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # Categorywise vendor counts (counts_only)
    vendor_counts = (
        Vendor.objects.values("category_id")
        .annotate(vendors_count=Count("id"))
        .order_by("-vendors_count")
    )
    category_ids = [vc["category_id"] for vc in vendor_counts if vc["category_id"] is not None]
    categories_by_id = Category.objects.in_bulk(category_ids)

    categorywise_vendors = []
    for row in vendor_counts:
        cid = row["category_id"]
        cat = categories_by_id.get(cid) if cid is not None else None
        categorywise_vendors.append(
            {
                "category_id": cid,
                "category_name": cat.name if cat else "Uncategorized",
                "vendors_count": row["vendors_count"],
            }
        )

    # Package activations total (sum of prices of all active subscriptions created last month)
    package_activations_total = (
        VendorSubscription.objects.filter(
            is_active=True,
            created_at__gte=last_month_start,
            created_at__lt=last_month_end,
        ).aggregate(total_price=Sum("plan__price"))["total_price"]
        or 0
    )

    payload = {
        "total_users": total_users,
        "total_vendors": total_vendors,
        "new_users_last_month": new_users_last_month,
        "earnings_last_month": str(earnings_last_month),
        "package_activations_total": str(package_activations_total),
        "categorywise_vendors": categorywise_vendors,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        "Admin dashboard summary retrieved successfully.",
        status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_best_performers_view(request: Request) -> Response:
    """
    Vendor-only leaderboard based on:
    - total bookings
    - total likes on vendor feeds
    - total comments on vendor feeds
    Month filter: ?year=YYYY&month=MM
    """
    now = timezone.now()

    year_param = request.GET.get("year")
    month_param = request.GET.get("month")
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 20))
    page = max(page, 1)
    limit = max(limit, 1)

    # If year/month not provided, default to PREVIOUS month
    if not year_param or not month_param:
        prev_month_start, prev_month_end = _last_month_range()
        year = prev_month_start.year
        month = prev_month_start.month
    else:
        try:
            year = int(year_param)
            month = int(month_param)
            if month < 1 or month > 12:
                raise ValueError("Invalid month")
        except ValueError:
            return ResponseService.response(
                "BAD_REQUEST",
                {"detail": "Query params `year` and `month` must be valid numbers."},
                "Validation error",
                status.HTTP_400_BAD_REQUEST,
            )

    period_start = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if month == 12:
        period_end = period_start.replace(year=year + 1, month=1)
    else:
        period_end = period_start.replace(month=month + 1)

    qs = (
        Vendor.objects.select_related("user")
        .annotate(
            bookings_count=Count(
                "bookings",
                filter=Q(bookings__booking_date__gte=period_start, bookings__booking_date__lt=period_end),
                distinct=True,
            ),
            likes_count=Count(
                "posts__likes",
                filter=Q(posts__likes__created_at__gte=period_start, posts__likes__created_at__lt=period_end),
                distinct=True,
            ),
            comments_count=Count(
                "posts__comments",
                filter=Q(posts__comments__created_at__gte=period_start, posts__comments__created_at__lt=period_end),
            ),
            followers_count_at_period=Count(
                "followers",
                filter=Q(followers__created_at__gte=period_start, followers__created_at__lt=period_end),
            ),
        )
        .order_by("-bookings_count", "-likes_count", "-comments_count", "-followers_count_at_period", "id")
    )

    total = qs.count()
    offset = (page - 1) * limit
    items = list(qs[offset : offset + limit])
    next_page = page + 1 if offset + limit < total else None

    payload_items = []
    for idx, vendor in enumerate(items, start=offset + 1):
        full_name = ""
        if vendor.user:
            full_name = f"{vendor.user.first_name} {vendor.user.last_name}".strip()
        payload_items.append(
            {
                "rank": idx,
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "owner_user_id": vendor.user_id,
                "owner_name": full_name,
                "bookings_count": vendor.bookings_count,
                "likes_count": vendor.likes_count,
                "comments_count": vendor.comments_count,
                "followers_count": vendor.followers_count_at_period,
                "performance_score": (
                    vendor.bookings_count + vendor.likes_count + vendor.comments_count + vendor.followers_count_at_period
                ),
            }
        )

    return ResponseService.response(
        "SUCCESS",
        {
            "year": year,
            "month": month,
            "period_start": period_start,
            "period_end": period_end,
            "items": payload_items,
            "total": total,
            "next_page": next_page,
        },
        "Best performers retrieved successfully.",
        status.HTTP_200_OK,
    )

