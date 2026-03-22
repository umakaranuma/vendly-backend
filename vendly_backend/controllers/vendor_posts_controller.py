from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

import mServices.ResponseService as ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import Post, PostMedia, Vendor


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
from vendly_backend.supabase_media import (
    MediaValidationError,
    SupabaseNotConfiguredError,
    upload_django_file,
)


def _is_multipart(request: Request) -> bool:
    ct = (request.content_type or "").lower()
    return "multipart/form-data" in ct


def _create_post_from_payload(request: Request, vendor) -> Response:
    data = request.data
    caption = data.get("caption", "") or ""
    media_list = data.get("media") or []
    return _persist_post(vendor, caption, media_list)


def _create_post_from_multipart(request: Request, vendor) -> Response:
    caption = (request.POST.get("caption") or "").strip()
    files = []
    files.extend(request.FILES.getlist("media_file"))
    if not files:
        files.extend(request.FILES.getlist("media_files"))
    if not files:
        single = request.FILES.get("media_file")
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


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def vendor_posts_view(request: Request) -> Response:
    vendor, err = _require_vendor(request)
    if err is not None:
        return err

    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))

            query = (
                QueryBuilderService("posts")
                .select("posts.id", "posts.caption", "posts.like_count", "posts.comment_count", "posts.created_at")
                .apply_conditions(f'{{"vendor_id": {vendor.id}}}', ["vendor_id"], "", [])
                .paginate(page, limit, ["posts.created_at"], "posts.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Posts retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        if _is_multipart(request):
            return _create_post_from_multipart(request, vendor)
        return _create_post_from_payload(request, vendor)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vendor_post_create_view(request: Request) -> Response:
    """Alias for POST /api/vendor/posts — multipart or JSON body."""
    vendor, err = _require_vendor(request)
    if err is not None:
        return err
    if _is_multipart(request):
        return _create_post_from_multipart(request, vendor)
    return _create_post_from_payload(request, vendor)


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
