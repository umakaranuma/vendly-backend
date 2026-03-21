from django.db import models

from vendly_backend.models.core import CoreStatus, CoreUser


class Conversation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"
        app_label = "vendly_backend"


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="conversations")
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversation_participants"
        app_label = "vendly_backend"
        unique_together = ("conversation", "user")


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField(null=True, blank=True)
    attachment_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "messages"
        app_label = "vendly_backend"


class MessageReadReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="read_receipts")
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="read_receipts")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_read_receipts"
        app_label = "vendly_backend"
        unique_together = ("message", "user")


class ChatReport(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="chat_reports")
    reason_type = models.CharField(max_length=100, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    status = models.ForeignKey(
        CoreStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_reports",
    )
    admin_action_note = models.TextField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        CoreUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_chat_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_reports"
        app_label = "vendly_backend"


class ChatReportMessage(models.Model):
    report = models.ForeignKey(ChatReport, on_delete=models.CASCADE, related_name="reported_messages")
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reported_in")
    sender = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="messages_reported")
    sender_type = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_report_messages"
        app_label = "vendly_backend"
        unique_together = ("report", "message")
