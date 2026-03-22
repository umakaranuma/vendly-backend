"""Booking workflow statuses stored in ``core_statuses`` (``entity_type=booking``)."""

from __future__ import annotations

from functools import lru_cache

# Maps API / legacy name -> CoreStatus.status_type (seeded in migrations).
BOOKING_STATUS_TYPE_BY_NAME: dict[str, str] = {
    "pending": "booking_pending",
    "confirmed": "booking_confirmed",
    "completed": "booking_completed",
    "cancelled": "booking_cancelled",
}

ALLOWED_BOOKING_STATUS_NAMES = frozenset(BOOKING_STATUS_TYPE_BY_NAME.keys())

# CoreStatus.status_type values for bookings (e.g. booking_pending).
ALLOWED_BOOKING_STATUS_TYPES = frozenset(BOOKING_STATUS_TYPE_BY_NAME.values())


@lru_cache(maxsize=8)
def get_booking_status_ref(name: str):
    """
    Return CoreStatus for a booking status name (pending, confirmed, completed, cancelled).
    """
    from vendly_backend.models import CoreStatus

    key = (name or "").strip().lower()
    status_type = BOOKING_STATUS_TYPE_BY_NAME.get(key)
    if not status_type:
        raise ValueError(f"Invalid booking status: {name!r}")
    return CoreStatus.objects.get(status_type=status_type)
