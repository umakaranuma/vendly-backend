from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, BooleanField, Count, Exists, OuterRef, Prefetch, Value

from mServices.ResponseService import ResponseService
from vendly_backend.vendor_ratings import feed_post_vendor_rating_and_count
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import (
    Feed, FeedLike, FeedMedia, FeedComment, CommentLike, VendorFollower, Vendor
)
from vendly_backend.permissions import is_admin_user


def _serialize_feed_post(feed: Feed) -> dict:
    vendor = feed.vendor
    vu = vendor.user
    cat = vendor.category
    rating, review_count = feed_post_vendor_rating_and_count(feed)
    media_qs = feed.media.all()
    media_list = [
        {
            "id": m.id,
            "url": m.url,
            "is_video": m.is_video,
            "sort_order": m.sort_order,
        }
        for m in media_qs
    ]
    images = [m for m in media_list if not m["is_video"]]
    videos = [m for m in media_list if m["is_video"]]

    return {
        "id": feed.id,
        "vendor_id": vendor.id,
        "caption": feed.caption,
        "like_count": feed.like_count,
        "comment_count": feed.comment_count,
        "created_at": feed.created_at.isoformat() if feed.created_at else None,
        "updated_at": feed.updated_at.isoformat() if feed.updated_at else None,
        "is_liked_by_me": bool(getattr(feed, "is_liked_by_me", False)),
        "is_followed_by_me": bool(getattr(feed, "is_followed_by_me", False)),
        "media": media_list,
        "images": images,
        "videos": videos,
        "vendor": {
            "id": vendor.id,
            "name": vendor.name,
            "slug": vendor.slug,
            "city": vendor.city,
            "bio": vendor.bio,
            "rating": rating,
            "review_count": review_count,
            "price_from": str(vendor.price_from) if vendor.price_from is not None else None,
            "status": vendor.status,
            "category_id": vendor.category_id,
            "category": (
                {"id": cat.id, "name": cat.name, "slug": cat.slug}
                if cat
                else None
            ),
            "user": {
                "id": vu.id,
                "first_name": vu.first_name,
                "last_name": vu.last_name,
                "avatar_url": vu.avatar_url,
                "cover_url": vu.cover_url,
                "bio": vu.bio,
            },
        },
    }


def list_posts_impl(request: Request, vendor_id: int | None = None) -> Response:
    """
    Core feed list logic; safe to call from another DRF view (avoids nested @api_view).
    When ``vendor_id`` is set, only that vendor's posts are returned (same payload shape as the global feed).
    """
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        user = request.user

        base = (
            Feed.objects.select_related("vendor", "vendor__user", "vendor__category")
            .prefetch_related(
                Prefetch(
                    "media",
                    queryset=FeedMedia.objects.order_by("sort_order", "id"),
                )
            )
            .annotate(
                _vendor_reviews_count=Count("vendor__reviews"),
                _vendor_reviews_avg=Avg("vendor__reviews__rating"),
            )
            .order_by("-created_at")
        )
        if user.is_authenticated:
            base = base.annotate(
                is_liked_by_me=Exists(
                    FeedLike.objects.filter(feed_id=OuterRef("pk"), user_id=user.id)
                ),
                is_followed_by_me=Exists(
                    VendorFollower.objects.filter(vendor_id=OuterRef("vendor_id"), user_id=user.id)
                )
            )
        else:
            base = base.annotate(
                is_liked_by_me=Value(False, output_field=BooleanField()),
                is_followed_by_me=Value(False, output_field=BooleanField())
            )
        if vendor_id is not None:
            base = base.filter(vendor_id=vendor_id)

        paginator = Paginator(base, limit)
        page_obj = paginator.get_page(page)

        data = [_serialize_feed_post(p) for p in page_obj.object_list]

        result = {
            "total_records": paginator.count,
            "per_page": limit,
            "current_page": page_obj.number,
            "last_page": paginator.num_pages or 1,
            "data": data,
        }
        return ResponseService.response("SUCCESS", result, "Feeds retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


def retrieve_feed_post_impl(request: Request, feed_id: int) -> Response:
    """Single feed with the same payload as feed list items (media, vendor, is_liked_by_me, …)."""
    try:
        user = request.user
        try:
            qs = (
                Feed.objects.select_related("vendor", "vendor__user", "vendor__category")
                .prefetch_related(
                    Prefetch(
                        "media",
                        queryset=FeedMedia.objects.order_by("sort_order", "id"),
                    )
                )
                .annotate(
                    _vendor_reviews_count=Count("vendor__reviews"),
                    _vendor_reviews_avg=Avg("vendor__reviews__rating"),
                )
            )
            if user.is_authenticated:
                qs = qs.annotate(
                    is_liked_by_me=Exists(
                        FeedLike.objects.filter(feed_id=OuterRef("pk"), user_id=user.id)
                    ),
                    is_followed_by_me=Exists(
                        VendorFollower.objects.filter(vendor_id=OuterRef("vendor_id"), user_id=user.id)
                    )
                )
            else:
                qs = qs.annotate(
                    is_liked_by_me=Value(False, output_field=BooleanField()),
                    is_followed_by_me=Value(False, output_field=BooleanField())
                )
            feed = qs.get(pk=feed_id)
        except Feed.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {}, "Feed not found.", status.HTTP_404_NOT_FOUND)
        return ResponseService.response(
            "SUCCESS",
            _serialize_feed_post(feed),
            "Feed retrieved successfully.",
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_posts(request: Request) -> Response:
    return list_posts_impl(request)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_feed_like(request: Request, post_id: int) -> Response:
    try:
        feed = Feed.objects.get(id=post_id)
    except Feed.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Feed not found.", status.HTTP_404_NOT_FOUND)

    user = request.user
    with transaction.atomic():
        like, created = FeedLike.objects.get_or_create(feed=feed, user=user)
        if not created:
            like.delete()
            feed.like_count = max(0, feed.like_count - 1)
            msg = "Feed unliked."
        else:
            feed.like_count += 1
            msg = "Feed liked."
        feed.save(update_fields=["like_count"])
    
    return ResponseService.response("SUCCESS", {"like_count": feed.like_count, "is_liked": created}, msg)

@api_view(["GET", "POST", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def post_comments(request: Request, post_id: int) -> Response:
    try:
        feed = Feed.objects.get(id=post_id)
    except Feed.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Feed not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            query = (
                QueryBuilderService("feed_comments")
                .select("feed_comments.id", "feed_comments.text", "feed_comments.like_count", "feed_comments.created_at", "feed_comments.parent_comment_id", "feed_comments.deleted_at", "core_users.first_name", "core_users.last_name", "core_users.avatar_url")
                .leftJoin("core_users", "core_users.id", "feed_comments.created_by_id")
                .apply_conditions(f'{{"feed_id": {feed.id}}}', ["feed_id"], "deleted_at IS NULL", [])
                .paginate(page, limit, ["feed_comments.created_at"], "feed_comments.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Comments retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        text = request.data.get("text")
        parent_id = request.data.get("parent_id")
        
        if not text:
            return ResponseService.response("BAD_REQUEST", {"detail": "Text is required."}, "Validation error", status.HTTP_400_BAD_REQUEST)
        
        parent = None
        if parent_id:
            try:
                parent = FeedComment.objects.get(id=parent_id, feed=feed)
            except FeedComment.DoesNotExist:
                return ResponseService.response("BAD_REQUEST", {"detail": "Invalid parent comment."}, "Validation error", status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            comment = FeedComment.objects.create(feed=feed, created_by=request.user, text=text, parent_comment=parent)
            feed.comment_count += 1
            feed.save(update_fields=["comment_count"])

        payload = {
            "id": comment.id,
            "text": comment.text,
            "time_ago": "just now",
            "like_count": comment.like_count,
            "is_liked": False,
            "author_name": f"{request.user.first_name} {request.user.last_name}".strip(),
            "author_avatar_url": request.user.avatar_url,
            "parent_id": comment.parent_comment_id,
            "created_at": comment.created_at.isoformat()
        }
        return ResponseService.response("SUCCESS", payload, "Comment added successfully.", status.HTTP_201_CREATED)

    elif request.method == "PUT":
        comment_id = request.data.get("comment_id")
        text = request.data.get("text")
        is_hidden = request.data.get("is_hidden")

        try:
            comment = FeedComment.objects.get(id=comment_id, feed=feed)
        except FeedComment.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {}, "Comment not found.", status.HTTP_404_NOT_FOUND)

        is_owner = comment.created_by_id == request.user.id
        is_feed_vendor = feed.vendor.user_id == request.user.id
        is_admin = is_admin_user(request.user)

        if text is not None:
            if not is_owner and not is_admin:
                return ResponseService.response("FORBIDDEN", {}, "You cannot edit this comment.", status.HTTP_403_FORBIDDEN)
            comment.text = text
        
        if is_hidden is not None:
            if not is_feed_vendor and not is_admin:
                return ResponseService.response("FORBIDDEN", {}, "You cannot hide this comment.", status.HTTP_403_FORBIDDEN)
            comment.is_hidden = is_hidden
        
        comment.save()
        return ResponseService.response("SUCCESS", {"id": comment.id, "text": comment.text, "is_hidden": comment.is_hidden}, "Comment updated.")

    elif request.method == "DELETE":
        comment_id = request.data.get("comment_id") or request.GET.get("comment_id") 
        if not comment_id:
             return ResponseService.response("BAD_REQUEST", {}, "Comment ID required.")

        try:
            comment = FeedComment.objects.get(id=comment_id, feed=feed)
        except FeedComment.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {}, "Comment not found.", status.HTTP_404_NOT_FOUND)

        is_owner = comment.created_by_id == request.user.id
        is_feed_vendor = feed.vendor.user_id == request.user.id
        is_admin = is_admin_user(request.user)

        if not is_owner and not is_feed_vendor and not is_admin:
            return ResponseService.response("FORBIDDEN", {}, "You cannot delete this comment.", status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            from django.utils import timezone
            comment.deleted_at = timezone.now()
            comment.save(update_fields=["deleted_at"])
            feed.comment_count = max(0, feed.comment_count - 1)
            feed.save(update_fields=["comment_count"])

        return ResponseService.response("SUCCESS", {}, "Comment deleted.", status.HTTP_204_NO_CONTENT)

@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def vendor_follow(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Vendor not found.", status.HTTP_404_NOT_FOUND)

    user = request.user
    if request.method == "POST":
        follow, created = VendorFollower.objects.get_or_create(vendor=vendor, user=user)
        if created:
            vendor.followers_count += 1
            vendor.save(update_fields=["followers_count"])
        return ResponseService.response("SUCCESS", {"followed": True, "followers_count": vendor.followers_count}, "Vendor followed.")
    
    elif request.method == "DELETE":
        try:
            follow = VendorFollower.objects.get(vendor=vendor, user=user)
            follow.delete()
            vendor.followers_count = max(0, vendor.followers_count - 1)
            vendor.save(update_fields=["followers_count"])
        except VendorFollower.DoesNotExist:
            pass
        return ResponseService.response("SUCCESS", {"followers_count": vendor.followers_count}, "Vendor unfollowed.", status.HTTP_200_OK) # Changed to 200 to return data

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_like(request: Request, comment_id: int) -> Response:
    try:
        comment = FeedComment.objects.get(id=comment_id)
    except FeedComment.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Comment not found.", status.HTTP_404_NOT_FOUND)

    user = request.user
    like, created = CommentLike.objects.get_or_create(comment=comment, user=user)
    if created:
        comment.like_count += 1
        comment.save(update_fields=["like_count"])
        
    return ResponseService.response("SUCCESS", {"liked": True, "like_count": comment.like_count}, "Comment liked.")
