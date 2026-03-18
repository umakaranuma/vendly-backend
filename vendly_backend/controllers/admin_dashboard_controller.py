from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from vendly_backend.models import Booking, Category, CoreUser, Vendor
from vendly_backend.permissions import IsAdmin


def _last_month_range():
    now = timezone.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_day_this_month
    last_month_start = (first_day_this_month - timedelta(days=1)).replace(day=1)
    return last_month_start, last_month_end


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_dashboard_summary_view(request: Request) -> Response:
    last_month_start, last_month_end = _last_month_range()

    total_users = CoreUser.objects.count()
    total_vendors = Vendor.objects.count()

    new_users_last_month = CoreUser.objects.filter(
        created_at__gte=last_month_start, created_at__lt=last_month_end
    ).count()

    earnings_last_month = (
        Booking.objects.filter(
            status="completed",
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

    payload = {
        "total_users": total_users,
        "total_vendors": total_vendors,
        "new_users_last_month": new_users_last_month,
        "earnings_last_month": str(earnings_last_month),
        "categorywise_vendors": categorywise_vendors,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        "Admin dashboard summary retrieved successfully.",
        status.HTTP_200_OK,
    )

