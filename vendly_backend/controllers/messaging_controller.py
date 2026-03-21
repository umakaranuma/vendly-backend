from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import (
    ChatReport,
    ChatReportMessage,
    Conversation,
    ConversationParticipant,
    CoreStatus,
    CoreUser,
    Message,
)
from vendly_backend.permissions import IsAdmin

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def conversations_view(request: Request) -> Response:
    user = request.user
    
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            # Simple retrieval of conversations for current user
            query = (
                QueryBuilderService("conversation_participants")
                .select("conversations.id", "conversations.updated_at")
                .leftJoin("conversations", "conversations.id", "conversation_participants.conversation_id")
                .apply_conditions(f'{{"user_id": {user.id}}}', ["user_id"], "", [])
                .paginate(page, limit, ["conversations.updated_at"], "conversations.updated_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Conversations retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        partner_id = request.data.get("partner_id")
        if not partner_id:
            return ResponseService.response("BAD_REQUEST", {"detail": "partner_id is required."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        if partner_id == user.id:
            return ResponseService.response("BAD_REQUEST", {"detail": "Cannot start conversation with yourself."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        try:
            partner = CoreUser.objects.get(id=partner_id)
        except CoreUser.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {"detail": "Partner not found."}, "Validation error", status.HTTP_404_NOT_FOUND)
            
        # Check if conversation already exists
        existing_conversations = ConversationParticipant.objects.filter(user=user).values_list('conversation_id', flat=True)
        partner_conversations = ConversationParticipant.objects.filter(user=partner, conversation_id__in=existing_conversations).values_list('conversation_id', flat=True)
        
        if partner_conversations.exists():
            conversation_id = partner_conversations.first()
            return ResponseService.response("SUCCESS", {"id": conversation_id}, "Conversation already exists.", status.HTTP_200_OK)
            
        with transaction.atomic():
            conversation = Conversation.objects.create()
            ConversationParticipant.objects.create(conversation=conversation, user=user)
            ConversationParticipant.objects.create(conversation=conversation, user=partner)
            
        return ResponseService.response("SUCCESS", {"id": conversation.id}, "Conversation created successfully.", status.HTTP_201_CREATED)

@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def conversation_detail_view(request: Request, conversation_id: int) -> Response:
    try:
        participant = ConversationParticipant.objects.get(conversation_id=conversation_id, user=request.user)
    except ConversationParticipant.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Conversation not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return ResponseService.response("SUCCESS", {"id": conversation_id}, "Conversation details.")

    elif request.method == "DELETE":
        participant.delete()
        return ResponseService.response("SUCCESS", {}, "Left conversation.", status.HTTP_204_NO_CONTENT)

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def messages_view(request: Request, conversation_id: int) -> Response:
    try:
        participant = ConversationParticipant.objects.get(conversation_id=conversation_id, user=request.user)
    except ConversationParticipant.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Conversation not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            query = (
                QueryBuilderService("messages")
                .select("messages.id", "messages.sender_id", "messages.text", "messages.attachment_url", "messages.created_at")
                .apply_conditions(f'{{"conversation_id": {conversation_id}}}', ["conversation_id"], "", [])
                .paginate(page, limit, ["messages.created_at"], "messages.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Messages retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
            
    elif request.method == "POST":
        text = request.data.get("text")
        attachment_url = request.data.get("attachment_url")
        
        if not text and not attachment_url:
            return ResponseService.response("BAD_REQUEST", {"detail": "text or attachment_url is required."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        message = Message.objects.create(
            conversation_id=conversation_id,
            sender=request.user,
            text=text,
            attachment_url=attachment_url
        )
        
        # update conversation updated_at
        conversation = message.conversation
        conversation.save(update_fields=["updated_at"])
        
        payload = {
            "id": message.id,
            "sender_id": message.sender_id,
            "text": message.text,
            "attachment_url": message.attachment_url,
            "created_at": message.created_at
        }
        return ResponseService.response("SUCCESS", payload, "Message sent successfully.", status.HTTP_201_CREATED)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def read_messages_view(request: Request, conversation_id: int) -> Response:
    try:
        participant = ConversationParticipant.objects.get(conversation_id=conversation_id, user=request.user)
    except ConversationParticipant.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Conversation not found.", status.HTTP_404_NOT_FOUND)
    
    return ResponseService.response("SUCCESS", {}, "Messages marked as read.", status.HTTP_204_NO_CONTENT)


def _sender_type_from_role(user: CoreUser) -> str:
    role_name = (getattr(getattr(user, "role", None), "name", "") or "").lower()
    if role_name == "vendor":
        return "vendor"
    if role_name == "customer":
        return "customer"
    return "user"


CHAT_REPORT_STATUS_TYPE_PREFIX = "chat_report_"


def _get_chat_report_status(status_value: str) -> CoreStatus | None:
    return CoreStatus.objects.filter(
        entity_type="chat_report",
        status_type=f"{CHAT_REPORT_STATUS_TYPE_PREFIX}{status_value}",
    ).first()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report_chat_messages_view(request: Request, conversation_id: int) -> Response:
    user = request.user
    try:
        ConversationParticipant.objects.get(conversation_id=conversation_id, user=user)
    except ConversationParticipant.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Conversation not found.", status.HTTP_404_NOT_FOUND)

    message_ids = request.data.get("message_ids") or []
    reason_type = (request.data.get("reason_type") or "").strip()
    reason = request.data.get("reason")
    if not isinstance(message_ids, list) or not message_ids:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "message_ids is required and must be a list."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )
    if len(message_ids) > 5:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "You can report at most 5 messages at a time."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )
    unique_message_ids = list(dict.fromkeys(message_ids))
    messages = list(
        Message.objects.select_related("sender")
        .filter(conversation_id=conversation_id, id__in=unique_message_ids)
    )
    message_map = {m.id: m for m in messages}
    missing = [mid for mid in unique_message_ids if mid not in message_map]
    if missing:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Some message_ids are invalid for this chat.", "invalid_message_ids": missing},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )
    default_status = _get_chat_report_status("open")
    if default_status is None:
        return ResponseService.response(
            "BAD_REQUEST",
            {
                "detail": "Default status `open` is not configured in core_statuses.",
                "expected_status_type": "chat_report_open",
            },
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        report = ChatReport.objects.create(
            conversation_id=conversation_id,
            reporter=user,
            reason_type=reason_type or None,
            reason=reason,
            status=default_status,
        )
        to_create = []
        for mid in unique_message_ids:
            msg = message_map[mid]
            to_create.append(
                ChatReportMessage(
                    report=report,
                    message=msg,
                    sender=msg.sender,
                    sender_type=_sender_type_from_role(msg.sender),
                )
            )
        ChatReportMessage.objects.bulk_create(to_create)

    return ResponseService.response(
        "SUCCESS",
        {
            "report_id": report.id,
            "conversation_id": conversation_id,
            "reason_type": report.reason_type,
            "status": report.status.name if report.status else None,
            "message_ids": unique_message_ids,
        },
        "Chat report submitted successfully.",
        status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_chat_reports_view(request: Request) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
    except ValueError:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "page and limit must be valid integers."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    page = max(page, 1)
    limit = max(limit, 1)
    conversation_id = request.GET.get("conversation_id")
    reporter_id = request.GET.get("reporter_id")
    report_status = (request.GET.get("status") or "").strip().lower()
    reason_type = (request.GET.get("reason_type") or "").strip()

    query = (
        QueryBuilderService("chat_reports")
        .select(
            "chat_reports.id",
            "chat_reports.conversation_id",
            "chat_reports.reporter_id",
            "chat_reports.reason_type",
            "chat_reports.reason",
            "chat_reports.status_id",
            "chat_reports.admin_action_note",
            "chat_reports.reviewed_by_id",
            "chat_reports.reviewed_at",
            "chat_reports.created_at",
            "core_users.first_name as reporter_first_name",
            "core_users.last_name as reporter_last_name",
            "core_roles.name as reporter_role",
            "core_statuses.name as status",
            "core_statuses.status_type as status_type",
        )
        .leftJoin("core_users", "core_users.id", "chat_reports.reporter_id")
        .leftJoin("core_roles", "core_roles.id", "core_users.role_id")
        .leftJoin("core_statuses", "core_statuses.id", "chat_reports.status_id")
    )
    if conversation_id:
        query = query.apply_conditions(f'{{"conversation_id": {int(conversation_id)}}}', ["conversation_id"], "", [])
    if reporter_id:
        query = query.apply_conditions(f'{{"reporter_id": {int(reporter_id)}}}', ["reporter_id"], "", [])
    if report_status:
        status_ref = _get_chat_report_status(report_status)
        if status_ref is None:
            return ResponseService.response(
                "BAD_REQUEST",
                {"detail": "Invalid status filter. Add this status in core_statuses for entity_type=chat_report."},
                "Validation error",
                status.HTTP_400_BAD_REQUEST,
            )
        query = query.apply_conditions(f'{{"status_id": {status_ref.id}}}', ["status_id"], "", [])
    if reason_type:
        query = query.apply_conditions(f'{{"reason_type": "{reason_type}"}}', ["reason_type"], "", [])
    reports_page = query.paginate(page, limit, ["chat_reports.created_at"], "chat_reports.created_at", "desc")

    report_items = reports_page.get("items", []) if isinstance(reports_page, dict) else []
    report_ids = [item.get("id") for item in report_items if item.get("id") is not None]
    messages_by_report = {}
    if report_ids:
        messages = (
            ChatReportMessage.objects.select_related("message", "sender")
            .filter(report_id__in=report_ids)
            .order_by("id")
        )
        for row in messages:
            messages_by_report.setdefault(row.report_id, []).append(
                {
                    "message_id": row.message_id,
                    "chat_id": row.message.conversation_id if row.message else None,
                    "text": row.message.text if row.message else None,
                    "attachment_url": row.message.attachment_url if row.message else None,
                    "message_created_at": row.message.created_at if row.message else None,
                    "sender_id": row.sender_id,
                    "sender_type": row.sender_type,
                    "sender_first_name": row.sender.first_name if row.sender else None,
                    "sender_last_name": row.sender.last_name if row.sender else None,
                }
            )

    for item in report_items:
        item["reported_messages"] = messages_by_report.get(item.get("id"), [])

    return ResponseService.response(
        "SUCCESS",
        reports_page,
        "Chat reports retrieved successfully.",
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_chat_report_update_view(request: Request, report_id: int) -> Response:
    try:
        report = ChatReport.objects.get(id=report_id)
    except ChatReport.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Chat report not found.", status.HTTP_404_NOT_FOUND)

    new_status = request.data.get("status")
    action_note = request.data.get("admin_action_note")
    if new_status is None and action_note is None:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Provide `status` and/or `admin_action_note`."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    update_fields = []
    if new_status is not None:
        new_status = str(new_status).strip().lower()
        status_ref = _get_chat_report_status(new_status)
        if status_ref is None:
            return ResponseService.response(
                "BAD_REQUEST",
                {
                    "detail": "Invalid status. Add this status in core_statuses for entity_type=chat_report.",
                    "expected_status_type": f"{CHAT_REPORT_STATUS_TYPE_PREFIX}{new_status}",
                },
                "Validation error",
                status.HTTP_400_BAD_REQUEST,
            )
        report.status = status_ref
        update_fields.append("status")

    if action_note is not None:
        report.admin_action_note = action_note
        update_fields.append("admin_action_note")

    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    update_fields.extend(["reviewed_by", "reviewed_at", "updated_at"])
    report.save(update_fields=update_fields)

    payload = {
        "id": report.id,
        "status": report.status.name if report.status else None,
        "status_type": report.status.status_type if report.status else None,
        "status_id": report.status_id,
        "admin_action_note": report.admin_action_note,
        "reviewed_by_id": report.reviewed_by_id,
        "reviewed_at": report.reviewed_at,
    }
    return ResponseService.response("SUCCESS", payload, "Chat report updated successfully.")
