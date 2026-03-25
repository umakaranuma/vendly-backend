"""Keep `vendors.rating` and `vendors.review_count` in sync with `vendor_reviews`."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count

from vendly_backend.models import Vendor, VendorReview


def _quantize_rating(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def sync_vendor_rating_from_reviews(vendor_id: int) -> None:
    """Set average rating and count from `vendor_reviews` for one vendor."""
    agg = VendorReview.objects.filter(vendor_id=vendor_id).aggregate(
        avg=Avg("rating"),
        cnt=Count("id"),
    )
    cnt = int(agg["cnt"] or 0)
    if cnt == 0:
        Vendor.objects.filter(pk=vendor_id).update(
            review_count=0,
            rating=Decimal("0.00"),
        )
        return
    Vendor.objects.filter(pk=vendor_id).update(
        review_count=cnt,
        rating=_quantize_rating(agg["avg"]),
    )


def sync_all_vendor_ratings_from_reviews() -> int:
    """Backfill: update cached stats for every vendor that has at least one review."""
    ids = VendorReview.objects.values_list("vendor_id", flat=True).distinct()
    for vid in ids:
        sync_vendor_rating_from_reviews(vid)
    return len(ids)


def public_vendor_rating_and_count(vendor) -> tuple[float, int]:
    """
    Rating/count shown on public vendor APIs: from ORM annotations when present
    (aggregates over ``vendor_reviews``), else denormalized columns on ``Vendor``.
    """
    cnt = getattr(vendor, "_reviews_count", None)
    avg = getattr(vendor, "_reviews_avg", None)
    if cnt is not None:
        return (float(avg) if avg is not None else 0.0, int(cnt))
    r = vendor.rating
    return (float(r) if r is not None else 0.0, int(vendor.review_count or 0))


def feed_post_vendor_rating_and_count(feed) -> tuple[float, int]:
    """Same as public vendor stats, for feed rows annotated on ``Feed``."""
    cnt = getattr(feed, "_vendor_reviews_count", None)
    avg = getattr(feed, "_vendor_reviews_avg", None)
    if cnt is not None:
        return (float(avg) if avg is not None else 0.0, int(cnt))
    v = feed.vendor
    r = v.rating
    return (float(r) if r is not None else 0.0, int(v.review_count or 0))
