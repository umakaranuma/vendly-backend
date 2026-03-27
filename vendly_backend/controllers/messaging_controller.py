from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from mServices.ValidatorService import ValidatorService
from vendly_backend.models import (
    ChatReport,
    ChatReportMessage,
    Conversation,
    ConversationParticipant,
    CoreStatus,
    CoreUser,
    Message,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def conversations_view(request: Request) -> Response:
    user = request.user
    
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            # Fetch conversations the user is part of
            user_participants = ConversationParticipant.objects.filter(user=user).select_related("conversation")
            
            conversations_data = []
            for up in user_participants:
                conv = up.conversation
                # Find the OTHER participant (partner)
                partner_participant = ConversationParticipant.objects.filter(conversation=conv).exclude(user=user).select_related("user").first()
                
                if not partner_participant:
                    continue
                
                partner = partner_participant.user
                
                # Get the last message
                last_msg = Message.objects.filter(conversation=conv).order_by("-created_at").first()
                
                conversations_data.append({
                    "id": conv.id,
                    "updated_at": conv.updated_at,
                    "partner": {
                        "id": partner.id,
                        "first_name": partner.first_name,
                        "last_name": partner.last_name,
                        "avatar_url": partner.avatar_url,
                        "role": partner.role.name if partner.role else "user"
                    },
                    "last_message": {
                        "text": last_msg.text if last_msg else None,
                        "attachment_url": last_msg.attachment_url if last_msg else None,
                        "created_at": last_msg.created_at if last_msg else None,
                        "is_deleted": last_msg.is_deleted if last_msg else False,
                        "sender_id": last_msg.sender_id if last_msg else None,
                    } if last_msg else None
                })
            
            # Sort by updated_at desc
            conversations_data.sort(key=lambda x: x["updated_at"], reverse=True)
            
            # Manual pagination (simplified for now as conversation lists are usually small)
            start = (page - 1) * limit
            end = start + limit
            paginated_data = {
                "items": [conversations_data[i] for i in range(start, min(end, len(conversations_data)))],
                "total": len(conversations_data),
                "page": page,
                "limit": limit
            }
            
            return ResponseService.response("SUCCESS", paginated_data, "Conversations retrieved successfully.")
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
                .select(
                    "messages.id",
                    "messages.sender_id",
                    "messages.text",
                    "messages.attachment_url",
                    "messages.is_edited",
                    "messages.is_deleted",
                    "messages.created_at",
                    "core_users.first_name",
                    "core_users.last_name"
                )
                .leftJoin("core_users", "core_users.id", "messages.sender_id")
                .apply_conditions(f'{{"conversation_id": {conversation_id}}}', ["conversation_id"], "", [])
                .paginate(page, limit, ["messages.created_at"], "messages.created_at", "desc")
            )
            
            # Post-process messages to handle deleted state
            if "items" in query:
                for msg in query["items"]:
                    if msg.get("is_deleted"):
                        sender_name = f"{msg.get('first_name', '')} {msg.get('last_name', '')}".strip() or "User"
                        msg["text"] = f"This message was deleted by {sender_name}"
                        msg["attachment_url"] = None
                        
            return ResponseService.response("SUCCESS", query, "Messages retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
            
    elif request.method == "POST":
        text = request.data.get("text")
        attachment_url = request.data.get("attachment_url")
        
        # Validation: only text and image allowed, at least one required
        if not text and not attachment_url:
            return ResponseService.response("BAD_REQUEST", {"detail": "Message must contain either text or an image."}, "Validation error", status.HTTP_400_BAD_REQUEST)
        
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def read_messages_view(request: Request, conversation_id: int) -> Response:
    try:
        participant = ConversationParticipant.objects.get(conversation_id=conversation_id, user=request.user)
        participant.last_read_at = timezone.now()
        participant.save(update_fields=["last_read_at"])
        return ResponseService.response("SUCCESS", {}, "Messages marked as read.", status.HTTP_200_OK)
    except ConversationParticipant.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Conversation not found.", status.HTTP_404_NOT_FOUND)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def message_detail_view(request: Request, message_id: int) -> Response:
    try:
        message = Message.objects.get(id=message_id, sender=request.user)
    except Message.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Message not found or you're not the sender.", status.HTTP_404_NOT_FOUND)

    # Time limit check (1 hour)
    time_diff = timezone.now() - message.created_at
    if time_diff.total_seconds() > 3600:
        return ResponseService.response("BAD_REQUEST", {"detail": "Messages can only be edited or deleted within 1 hour."}, "Time limit exceeded", status.HTTP_400_BAD_REQUEST)

    if request.method == "PATCH":
        text = request.data.get("text")
        if not text:
            return ResponseService.response("BAD_REQUEST", {"detail": "Text is required for editing."}, "Validation error", status.HTTP_400_BAD_REQUEST)
        
        message.text = text
        message.is_edited = True
        message.save(update_fields=["text", "is_edited", "updated_at"])
        
        return ResponseService.response("SUCCESS", {"id": message.id, "text": message.text, "is_edited": True}, "Message edited successfully.")

    elif request.method == "DELETE":
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        
        sender_name = f"{request.user.first_name} {request.user.last_name}".strip() or "User"
        return ResponseService.response("SUCCESS", {"id": message.id, "text": f"This message was deleted by {sender_name}"}, "Message deleted successfully.")


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

    data = request.data
    errors = ValidatorService.validate(
        data,
        rules={"message_ids": "required"},
        custom_messages={"message_ids.required": "message_ids is required."},
    )
    if errors:
        return ResponseService.response("VALIDATION_ERROR", errors, "Validation Error")

    message_ids = data.get("message_ids") or []
    reason_type = (data.get("reason_type") or "").strip()
    reason = data.get("reason")
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
@permission_classes([IsAuthenticated])
def admin_chat_reports_view(request: Request) -> Response:
    params = {
        "page": request.GET.get("page", 1),
        "limit": request.GET.get("limit", 20),
    }
    errors = ValidatorService.validate(
        params,
        rules={"page": "required", "limit": "required"},
        custom_messages={},
    )
    if errors:
        return ResponseService.response("VALIDATION_ERROR", errors, "Validation Error")

    try:
        page = int(params["page"])
        limit = int(params["limit"])
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
@permission_classes([IsAuthenticated])
def admin_chat_report_update_view(request: Request, report_id: int) -> Response:
    try:
        report = ChatReport.objects.get(id=report_id)
    except ChatReport.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Chat report not found.", status.HTTP_404_NOT_FOUND)

    data = request.data
    new_status = data.get("status")
    action_note = data.get("admin_action_note")
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
