from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import Post, PostLike, Comment, CommentLike

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_posts(request: Request) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        
        # In a real scenario we'd use QueryBuilderService properly to join media and vendors
        # For simplicity based on SKILL.md:
        query = (
            QueryBuilderService("posts")
            .select("posts.id", "posts.vendor_id", "posts.caption", "posts.like_count", "posts.comment_count", "posts.created_at")
            .paginate(page, limit, ["posts.created_at"], "posts.created_at", "desc")
        )
        return ResponseService.response("SUCCESS", query, "Posts retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

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
