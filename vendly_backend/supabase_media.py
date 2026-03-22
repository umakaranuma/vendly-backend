"""
Upload helpers for Supabase Storage (service role on the backend only).
Public URLs follow: {SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}
"""

from __future__ import annotations

import os
import uuid

from django.conf import settings


class SupabaseNotConfiguredError(RuntimeError):
    pass


class SupabaseBucketNotFoundError(RuntimeError):
    """The Storage bucket name in settings does not exist in this Supabase project."""

    pass


class MediaValidationError(ValueError):
    pass


ALLOWED_FOLDERS = frozenset({"profile", "vendors", "posts", "chat"})

ALLOWED_IMAGE_EXT = frozenset({"jpg", "jpeg", "png", "webp"})
ALLOWED_VIDEO_EXT = frozenset({"mp4"})

IMAGE_MAX_BYTES = 5 * 1024 * 1024
VIDEO_MAX_BYTES = 50 * 1024 * 1024

_EXT_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "mp4": "video/mp4",
}


def _client():
    url = (getattr(settings, "SUPABASE_URL", None) or "").strip()
    key = (getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None) or "").strip()
    if not url or not key:
        raise SupabaseNotConfiguredError(
            "SUPABASE_URL and a secret key must be set (SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY)."
        )
    from supabase import create_client

    return create_client(url, key)


def _normalize_ext(filename: str) -> str:
    base = os.path.basename(filename or "")
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def classify_upload(filename: str) -> tuple[str, bool]:
    ext = _normalize_ext(filename)
    if ext in ALLOWED_IMAGE_EXT:
        return ext, False
    if ext in ALLOWED_VIDEO_EXT:
        return ext, True
    raise MediaValidationError(
        f"Unsupported file type '.{ext}'. Allowed: "
        + ", ".join(sorted(ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT))
    )


def validate_upload_size(uploaded_file, *, is_video: bool) -> None:
    max_bytes = VIDEO_MAX_BYTES if is_video else IMAGE_MAX_BYTES
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > max_bytes:
        kind = "video" if is_video else "image"
        raise MediaValidationError(
            f"{kind.capitalize()} exceeds maximum size of {max_bytes // (1024 * 1024)}MB."
        )


def public_url_for_storage_path(storage_path: str) -> str:
    storage_path = storage_path.lstrip("/")
    bucket = getattr(settings, "SUPABASE_STORAGE_BUCKET", "media")
    base = (getattr(settings, "SUPABASE_URL", "") or "").rstrip("/")
    return f"{base}/storage/v1/object/public/{bucket}/{storage_path}"


def upload_bytes_to_supabase(
    folder: str,
    owner_segment: str,
    file_bytes: bytes,
    *,
    ext: str,
    content_type: str,
) -> str:
    folder = folder.strip().strip("/")
    if folder not in ALLOWED_FOLDERS:
        raise MediaValidationError(f"Invalid storage folder '{folder}'.")

    safe_ext = ext.lower().lstrip(".")
    if safe_ext not in ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT:
        raise MediaValidationError("Invalid extension for upload.")

    object_path = f"{folder}/{owner_segment}/{uuid.uuid4().hex}.{safe_ext}"
    bucket = getattr(settings, "SUPABASE_STORAGE_BUCKET", "media")

    supabase = _client()
    try:
        supabase.storage.from_(bucket).upload(
            object_path,
            file_bytes,
            file_options={"content-type": content_type},
        )
    except Exception as exc:
        err_text = str(exc).lower()
        if "bucket not found" in err_text or (
            "404" in str(exc) and "bucket" in err_text
        ):
            raise SupabaseBucketNotFoundError(
                f"Supabase Storage bucket '{bucket}' was not found. "
                "In the Supabase Dashboard go to Storage → create a bucket with this name "
                "(or set SUPABASE_BUCKET / SUPABASE_STORAGE_BUCKET in .env to an existing bucket). "
                "For public URLs, mark the bucket as public or add a policy for uploads."
            ) from exc
        raise
    return public_url_for_storage_path(object_path)


def upload_django_file(
    folder: str,
    owner_segment: str,
    uploaded_file,
    *,
    allow_video: bool = True,
) -> tuple[str, bool]:
    """
    Reads the uploaded file, validates type/size, uploads to Supabase.
    Returns (public_url, is_video).
    """
    ext, is_video = classify_upload(getattr(uploaded_file, "name", "") or "")
    if not allow_video and is_video:
        raise MediaValidationError("Only image files are allowed for this upload.")
    validate_upload_size(uploaded_file, is_video=is_video)

    raw = uploaded_file.read()
    if len(raw) > (VIDEO_MAX_BYTES if is_video else IMAGE_MAX_BYTES):
        kind = "video" if is_video else "image"
        raise MediaValidationError(
            f"{kind.capitalize()} exceeds maximum size of "
            f"{(VIDEO_MAX_BYTES if is_video else IMAGE_MAX_BYTES) // (1024 * 1024)}MB."
        )

    mime = _EXT_TO_MIME.get(ext.lower(), "application/octet-stream")
    url = upload_bytes_to_supabase(folder, owner_segment, raw, ext=ext, content_type=mime)
    return url, is_video
