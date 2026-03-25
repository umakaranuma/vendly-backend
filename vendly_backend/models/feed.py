from django.db import models

from vendly_backend.models.core import CoreUser
from vendly_backend.models.vendors import Vendor


class Feed(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="feeds")
    caption = models.TextField(null=True, blank=True)
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feeds"
        app_label = "vendly_backend"


class FeedMedia(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="media", db_column="feed_id")
    url = models.TextField()
    is_video = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "feed_media"
        app_label = "vendly_backend"


class FeedLike(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="likes", db_column="feed_id")
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="feed_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feed_likes"
        app_label = "vendly_backend"
        unique_together = ("feed", "user")





class FeedComment(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="comments", db_column="feed_id")
    created_by = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="feed_comments", db_column="created_by_id")
    parent_comment = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies", db_column="parent_comment_id")
    text = models.TextField()
    is_hidden = models.BooleanField(default=False)
    like_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "feed_comments"
        app_label = "vendly_backend"


class CommentLike(models.Model):
    comment = models.ForeignKey(FeedComment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="comment_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comment_likes"
        app_label = "vendly_backend"
        unique_together = ("comment", "user")
