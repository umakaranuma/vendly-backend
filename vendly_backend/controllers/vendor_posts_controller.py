from __future__ import annotations

import json

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

import mServices.ResponseService as ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from mServices.ValidatorService import ValidatorService
from vendly_backend.controllers.feed_controller import list_posts_impl, retrieve_feed_post_impl
from vendly_backend.models import Post, PostMedia, Vendor
from vendly_backend.permissions import is_admin_user
from vendly_backend.supabase_media import (
    MediaValidationError,
    SupabaseBucketNotFoundError,
    SupabaseNotConfiguredError,
    upload_django_file,
)


def _require_vendor(request: Request):
    """Return (vendor, None) or (None, error Response) if the user has no vendor profile."""
    try:
        return request.user.vendor, None
    except Vendor.DoesNotExist:
        return None, ResponseService.response(
            "FORBIDDEN",
            {"detail": "Only vendor accounts can create or manage feed posts."},
            "Vendor profile required.",
            status.HTTP_403_FORBIDDEN,
        )


def _is_multipart(request: Request) -> bool:
    """
    True when the client intends a multipart upload (caption + files).
    Explicit JSON is never treated as multipart so we do not hit Supabase upload
    for application/json bodies (same behavior as dedicated create routes).
    """
    ct = (request.content_type or "").lower()
    if "application/json" in ct:
        return False
    if "multipart/form-data" in ct:
        return True
    # Clients sometimes omit or mis-set Content-Type; Django still populates FILES.
    return bool(getattr(request, "FILES", None))


def list_vendor_posts(request: Request, vendor) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        search_string = request.GET.get("search", "") or ""
        sort_by = (request.GET.get("sort_by") or "created_at").strip().lower()
        sort_dir = (request.GET.get("sort_dir") or "desc").strip().lower()

        filters: dict[str, object] = {"vendor_id": vendor.id}
        raw_filters = request.GET.get("filters")
        if raw_filters is not None and str(raw_filters).strip() != "":
            extra = json.loads(raw_filters)
            if not isinstance(extra, dict):
                raise ValueError("filters must be a JSON object")
            extra.pop("vendor_id", None)
            if "id" in extra:
                filters["id"] = int(extra["id"])

        sort_map = {
            "created_at": "posts.created_at",
            "like_count": "posts.like_count",
            "comment_count": "posts.comment_count",
        }
        if sort_by not in sort_map:
            raise ValueError("Invalid sort_by")
        sort_col = sort_map[sort_by]
        if sort_dir not in ("asc", "desc"):
            raise ValueError("Invalid sort_dir")

        filter_json = json.dumps(filters)
        filter_keys = list(filters.keys())

        query = (
            QueryBuilderService("posts")
            .select(
                "posts.id",
                "posts.caption",
                "posts.like_count",
                "posts.comment_count",
                "posts.created_at",
            )
            .apply_conditions(
                filter_json,
                filter_keys,
                search_string,
                ["posts.caption"],
            )
            .paginate(page, limit, [sort_col], sort_col, sort_dir)
        )
        return ResponseService.response("SUCCESS", query, "Posts retrieved successfully.")
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


def retrieve_post(request: Request, post_id: int) -> Response:
    return retrieve_feed_post_impl(request, post_id)


def update_vendor_post(request: Request, vendor, post_id: int) -> Response:
    try:
        post = Post.objects.get(id=post_id, vendor=vendor)
        if _is_multipart(request):
            caption = request.POST.get("caption")
            if caption is not None:
                post.caption = (caption or "").strip()
            files = []
            files.extend(request.FILES.getlist("media_file"))
            if not files:
                files.extend(request.FILES.getlist("media_files"))
            if not files:
                files.extend(request.FILES.getlist("media"))
            if not files:
                single = request.FILES.get("media_file") or request.FILES.get("media")
                if single:
                    files.append(single)
            if files:
                post.media.all().delete()
                owner_key = str(vendor.id)
                media_list = []
                for f in files:
                    try:
                        url, is_video = upload_django_file("posts", owner_key, f)
                    except SupabaseNotConfiguredError:
                        return ResponseService.response(
                            "INTERNAL_SERVER_ERROR",
                            {"detail": "Storage is not configured."},
                            "Storage is not configured.",
                            status.HTTP_503_SERVICE_UNAVAILABLE,
                        )
                    except SupabaseBucketNotFoundError as e:
                        return ResponseService.response(
                            "INTERNAL_SERVER_ERROR",
                            {"detail": str(e)},
                            "Storage bucket not found.",
                            status.HTTP_503_SERVICE_UNAVAILABLE,
                        )
                    except MediaValidationError as e:
                        return ResponseService.response(
                            "VALIDATION_ERROR",
                            {"media_file": [str(e)]},
                            "Validation error",
                            status.HTTP_400_BAD_REQUEST,
                        )
                    except Exception as e:
                        return ResponseService.response(
                            "INTERNAL_SERVER_ERROR",
                            {"detail": str(e)},
                            "Upload failed.",
                            status.HTTP_502_BAD_GATEWAY,
                        )
                    media_list.append({"url": url, "is_video": is_video})
                for i, media_item in enumerate(media_list):
                    PostMedia.objects.create(
                        post=post,
                        url=media_item["url"],
                        is_video=media_item.get("is_video", False),
                        sort_order=i,
                    )
            post.save()
        else:
            data = request.data
            errors = ValidatorService.validate(
                data,
                rules={"caption": "nullable|string"},
                custom_messages={},
            )
            if errors:
                return ResponseService.response(
                    "VALIDATION_ERROR",
                    errors,
                    "Validation Error",
                    status.HTTP_400_BAD_REQUEST,
                )
            if "caption" in data:
                post.caption = (data.get("caption") or "") or ""
            if "media" in data:
                media_list, media_err = _validate_media_payload(data.get("media"))
                if media_err is not None:
                    return media_err
                post.media.all().delete()
                for i, media_item in enumerate(media_list or []):
                    if isinstance(media_item, dict) and "url" in media_item:
                        PostMedia.objects.create(
                            post=post,
                            url=media_item["url"],
                            is_video=media_item.get("is_video", False),
                            sort_order=i,
                        )
            post.save()

        post.refresh_from_db()
        media_qs = post.media.order_by("sort_order")
        payload = {
            "id": post.id,
            "caption": post.caption,
            "created_at": post.created_at,
            "media": [
                {"url": m.url, "is_video": m.is_video, "sort_order": m.sort_order}
                for m in media_qs
            ],
        }
        return ResponseService.response("SUCCESS", payload, "Post updated successfully.")
    except Post.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return ResponseService.response(
            "VALIDATION_ERROR",
            getattr(e, "message_dict", None) or {"detail": [str(e)]},
            "Validation Error",
            status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


def _validate_media_payload(media_list) -> tuple[list | None, Response | None]:
    if media_list is None:
        return [], None
    if not isinstance(media_list, list):
        return None, ResponseService.response(
            "VALIDATION_ERROR",
            {"media": ["Media must be a list."]},
            "Validation Error",
            status.HTTP_400_BAD_REQUEST,
        )
    normalized = []
    for item in media_list:
        if not isinstance(item, dict) or "url" not in item:
            return None, ResponseService.response(
                "VALIDATION_ERROR",
                {"media": ["Each media item must be an object with a url."]},
                "Validation Error",
                status.HTTP_400_BAD_REQUEST,
            )
        normalized.append(
            {
                "url": item["url"],
                "is_video": bool(item.get("is_video", False)),
            }
        )
    return normalized, None


def create_vendor_post(request: Request, vendor) -> Response:
    try:
        if _is_multipart(request):
            caption = request.POST.get("caption") or ""
            errors = ValidatorService.validate(
                {"caption": caption},
                rules={"caption": "nullable|string"},
                custom_messages={},
            )
            if errors:
                return ResponseService.response(
                    "VALIDATION_ERROR",
                    errors,
                    "Validation Error",
                    status.HTTP_400_BAD_REQUEST,
                )
            return _create_post_from_multipart(request, vendor)

        data = request.data
        errors = ValidatorService.validate(
            data,
            rules={"caption": "nullable|string"},
            custom_messages={},
        )
        if errors:
            return ResponseService.response(
                "VALIDATION_ERROR",
                errors,
                "Validation Error",
                status.HTTP_400_BAD_REQUEST,
            )

        caption = data.get("caption", "") or ""
        media_list, media_err = _validate_media_payload(data.get("media"))
        if media_err is not None:
            return media_err

        return _persist_post(vendor, caption, media_list or [])
    except ValidationError as e:
        return ResponseService.response(
            "VALIDATION_ERROR",
            getattr(e, "message_dict", None) or {"detail": [str(e)]},
            "Validation Error",
            status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


def _create_post_from_multipart(request: Request, vendor) -> Response:
    caption = (request.POST.get("caption") or "").strip()
    files = []
    # Common field names from clients (Postman, Flutter, etc.)
    files.extend(request.FILES.getlist("media_file"))
    if not files:
        files.extend(request.FILES.getlist("media_files"))
    if not files:
        files.extend(request.FILES.getlist("media"))
    if not files:
        single = request.FILES.get("media_file") or request.FILES.get("media")
        if single:
            files.append(single)

    media_list = []
    owner_key = str(vendor.id)
    for f in files:
        try:
            url, is_video = upload_django_file("posts", owner_key, f)
        except SupabaseNotConfiguredError:
            return ResponseService.response(
                "INTERNAL_SERVER_ERROR",
                {"detail": "Storage is not configured."},
                "Storage is not configured.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SupabaseBucketNotFoundError as e:
            return ResponseService.response(
                "INTERNAL_SERVER_ERROR",
                {"detail": str(e)},
                "Storage bucket not found.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except MediaValidationError as e:
            return ResponseService.response(
                "VALIDATION_ERROR",
                {"media_file": [str(e)]},
                "Validation error",
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return ResponseService.response(
                "INTERNAL_SERVER_ERROR",
                {"detail": str(e)},
                "Upload failed.",
                status.HTTP_502_BAD_GATEWAY,
            )
        media_list.append({"url": url, "is_video": is_video})

    return _persist_post(vendor, caption, media_list)


def _persist_post(vendor, caption: str, media_list: list) -> Response:
    with transaction.atomic():
        post = Post.objects.create(vendor=vendor, caption=caption)

        for i, media_item in enumerate(media_list):
            if isinstance(media_item, dict) and "url" in media_item:
                PostMedia.objects.create(
                    post=post,
                    url=media_item["url"],
                    is_video=media_item.get("is_video", False),
                    sort_order=i,
                )

    media_qs = post.media.order_by("sort_order")
    payload = {
        "id": post.id,
        "caption": post.caption,
        "created_at": post.created_at,
        "media": [
            {"url": m.url, "is_video": m.is_video, "sort_order": m.sort_order}
            for m in media_qs
        ],
    }
    return ResponseService.response("SUCCESS", payload, "Post created successfully.", status.HTTP_201_CREATED)


def run_vendor_post_create(request: Request) -> Response:
    """Shared by POST /api/posts/create, POST /api/vendor/posts, and POST /api/posts."""
    vendor, err = _require_vendor(request)
    if err is not None:
        return err
    return create_vendor_post(request, vendor)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def vendor_posts_view(request: Request) -> Response:
    vendor, err = _require_vendor(request)
    if err is not None:
        return err
    if request.method == "GET":
        return list_vendor_posts(request, vendor)
    return create_vendor_post(request, vendor)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vendor_post_create_view(request: Request) -> Response:
    """Alias for POST /api/vendor/posts — multipart or JSON body."""
    return run_vendor_post_create(request)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def vendor_post_detail_view(request: Request, post_id: int) -> Response:
    vendor, err = _require_vendor(request)
    if err is not None:
        return err
    try:
        post = Post.objects.get(id=post_id, vendor=vendor)
        post.delete()
        return ResponseService.response("SUCCESS", {}, "Post deleted.", status.HTTP_204_NO_CONTENT)
    except Post.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def posts_collection_view(request: Request) -> Response:
    if request.method == "GET":
        # Same payload as /api/feed/posts (call impl directly — nested @api_view needs HttpRequest)
        return list_posts_impl(request)
    return run_vendor_post_create(request)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def posts_detail_view(request: Request, post_id: int) -> Response:
    if request.method == "GET":
        return retrieve_post(request, post_id)
    if request.method == "PUT":
        vendor, err = _require_vendor(request)
        if err is not None:
            return err
        return update_vendor_post(request, vendor, post_id)
    if is_admin_user(request.user):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)
        post.delete()
        return ResponseService.response("SUCCESS", {}, "Post deleted.", status.HTTP_204_NO_CONTENT)
    vendor, err = _require_vendor(request)
    if err is not None:
        return err
    try:
        post = Post.objects.get(id=post_id, vendor=vendor)
        post.delete()
        return ResponseService.response("SUCCESS", {}, "Post deleted.", status.HTTP_204_NO_CONTENT)
    except Post.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_posts_by_vendor_id_view(request: Request, vendor_id: int) -> Response:
    try:
        Vendor.objects.get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Vendor not found.", status.HTTP_404_NOT_FOUND)
    # Same rich payload as GET /api/posts and GET /api/feed/posts (media, vendor, is_liked_by_me, …)
    return list_posts_impl(request, vendor_id=vendor_id)
