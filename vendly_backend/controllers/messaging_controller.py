from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import Conversation, ConversationParticipant, Message, CoreUser

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
