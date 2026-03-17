from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import Post, PostMedia
from vendly_backend.permissions import IsVendor

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsVendor])
def vendor_posts_view(request: Request) -> Response:
    vendor = request.user.vendor
    
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
        data = request.data
        caption = data.get("caption", "")
        media_list = data.get("media", [])
        
        with transaction.atomic():
            post = Post.objects.create(vendor=vendor, caption=caption)
            
            for i, media_item in enumerate(media_list):
                if isinstance(media_item, dict) and "url" in media_item:
                    PostMedia.objects.create(
                        post=post,
                        url=media_item["url"],
                        is_video=media_item.get("is_video", False),
                        sort_order=i
                    )
        
        payload = {
            "id": post.id,
            "caption": post.caption,
            "created_at": post.created_at
        }
        return ResponseService.response("SUCCESS", payload, "Post created successfully.", status.HTTP_201_CREATED)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsVendor])
def vendor_post_detail_view(request: Request, post_id: int) -> Response:
    try:
        post = Post.objects.get(id=post_id, vendor=request.user.vendor)
        post.delete()
        return ResponseService.response("SUCCESS", {}, "Post deleted.", status.HTTP_204_NO_CONTENT)
    except Post.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Post not found.", status.HTTP_404_NOT_FOUND)
