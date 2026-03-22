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
from vendly_backend.models import Post, PostLike, PostMedia, Comment, CommentLike


def _serialize_feed_post(post: Post) -> dict:
    vendor = post.vendor
    vu = vendor.user
    cat = vendor.category
    rating, review_count = feed_post_vendor_rating_and_count(post)
    media_qs = post.media.all()
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
        "id": post.id,
        "vendor_id": vendor.id,
        "caption": post.caption,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "is_liked_by_me": bool(getattr(post, "is_liked_by_me", False)),
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
            Post.objects.select_related("vendor", "vendor__user", "vendor__category")
            .prefetch_related(
                Prefetch(
                    "media",
                    queryset=PostMedia.objects.order_by("sort_order", "id"),
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
                    PostLike.objects.filter(post_id=OuterRef("pk"), user_id=user.id)
                )
            )
        else:
            base = base.annotate(is_liked_by_me=Value(False, output_field=BooleanField()))
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
        return ResponseService.response("SUCCESS", result, "Posts retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


def retrieve_feed_post_impl(request: Request, post_id: int) -> Response:
    """Single post with the same payload as feed list items (media, vendor, is_liked_by_me, …)."""
    try:
        user = request.user
        try:
            qs = (
                Post.objects.select_related("vendor", "vendor__user", "vendor__category")
                .prefetch_related(
                    Prefetch(
                        "media",
                        queryset=PostMedia.objects.order_by("sort_order", "id"),
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
                        PostLike.objects.filter(post_id=OuterRef("pk"), user_id=user.id)
                    )
                )
            else:
                qs = qs.annotate(is_liked_by_me=Value(False, output_field=BooleanField()))
            post = qs.get(pk=post_id)
        except Post.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)
        return ResponseService.response(
            "SUCCESS",
            _serialize_feed_post(post),
            "Post retrieved successfully.",
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_posts(request: Request) -> Response:
    return list_posts_impl(request)

@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def post_like(request: Request, post_id: int) -> Response:
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)

    user = request.user
    if request.method == "POST":
        like, created = PostLike.objects.get_or_create(post=post, user=user)
        if created:
            post.like_count += 1
            post.save(update_fields=["like_count"])
        return ResponseService.response("SUCCESS", {"liked": True, "like_count": post.like_count}, "Post liked.")
    
    elif request.method == "DELETE":
        try:
            like = PostLike.objects.get(post=post, user=user)
            like.delete()
            post.like_count = max(0, post.like_count - 1)
            post.save(update_fields=["like_count"])
        except PostLike.DoesNotExist:
            pass
        return ResponseService.response("SUCCESS", {}, "Post unliked.", status.HTTP_204_NO_CONTENT)

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def post_comments(request: Request, post_id: int) -> Response:
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            query = (
                QueryBuilderService("comments")
                .select("comments.id", "comments.text", "comments.like_count", "comments.created_at", "core_users.first_name", "core_users.last_name", "core_users.avatar_url")
                .leftJoin("core_users", "core_users.id", "comments.user_id")
                .apply_conditions(f'{{"post_id": {post.id}}}', ["post_id"], "", [])
                .paginate(page, limit, ["comments.created_at"], "comments.created_at", "desc")
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
                parent = Comment.objects.get(id=parent_id, post=post)
            except Comment.DoesNotExist:
                return ResponseService.response("BAD_REQUEST", {"detail": "Invalid parent comment."}, "Validation error", status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            comment = Comment.objects.create(post=post, user=request.user, text=text, parent=parent)
            post.comment_count += 1
            post.save(update_fields=["comment_count"])

        payload = {
            "id": comment.id,
            "text": comment.text,
            "time_ago": "just now",
            "like_count": comment.like_count,
            "is_liked": False,
            "author_name": f"{request.user.first_name} {request.user.last_name}".strip(),
            "author_avatar_url": request.user.avatar_url
        }
        return ResponseService.response("SUCCESS", payload, "Comment added successfully.", status.HTTP_201_CREATED)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_like(request: Request, comment_id: int) -> Response:
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Comment not found.", status.HTTP_404_NOT_FOUND)

    user = request.user
    like, created = CommentLike.objects.get_or_create(comment=comment, user=user)
    if created:
        comment.like_count += 1
        comment.save(update_fields=["like_count"])
        
    return ResponseService.response("SUCCESS", {"liked": True, "like_count": comment.like_count}, "Comment liked.")
