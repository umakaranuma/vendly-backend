from __future__ import annotations

import logging
from typing import Any

from vendly_backend.models import AuditLog, CoreUser

logger = logging.getLogger(__name__)


def log_activity(
    *,
    actor: CoreUser | None,
    category: str,
    event: str,
    resource_type: str | None = None,
    resource_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """
    Persist a user activity event for admin auditing.
    """
    if actor is None or not getattr(actor, "id", None):
        return

    action = f"{(category or 'general').strip()}.{(event or 'event').strip()}"
    safe_payload = payload or {}

    try:
        AuditLog.objects.create(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=safe_payload,
        )
    except Exception as exc:  # pragma: no cover - logging should never break request flow
        logger.warning("Failed to write audit log. action=%s actor_id=%s error=%s", action, actor.id, exc)
