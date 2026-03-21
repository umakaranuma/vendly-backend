from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import InvitationTemplate, Invitation

@api_view(["GET"])

@permission_classes([IsAuthenticated])
def invitation_templates_view(request: Request) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        template_type = (request.GET.get("type") or "").strip()
        query = (
            QueryBuilderService("invitation_templates")
            .select(
                "invitation_templates.id",
                "invitation_templates.name",
                "invitation_templates.description",
                "invitation_templates.style",
                "invitation_templates.icon",
                "invitation_templates.invitation_type_id",
                "invitation_template_types.type_key as invitation_type",
            )
            .leftJoin(
                "invitation_template_types",
                "invitation_template_types.id",
                "invitation_templates.invitation_type_id",
            )
        )
        if template_type:
            query = query.apply_conditions(
                f'{{"invitation_template_types.type_key": "{template_type}"}}',
                ["invitation_template_types.type_key"],
                "",
                [],
            )
        query = query.paginate(
            page,
            limit,
            ["invitation_templates.sort_order", "invitation_templates.id"],
            "invitation_templates.sort_order",
            "asc",
        )
        return ResponseService.response("SUCCESS", query, "Templates retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def invitations_view(request: Request) -> Response:
    user = request.user
    
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            query = (
                QueryBuilderService("invitations")
                .select("invitations.id", "invitations.invitation_type", "invitations.event_type", "invitations.answers", "invitations.created_at")
                .apply_conditions(f'{{"user_id": {user.id}}}', ["user_id"], "", [])
                .paginate(page, limit, ["invitations.created_at"], "invitations.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Invitations retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        data = request.data
        invitation_type = data.get("invitation_type")
        event_type = data.get("event_type")
        answers = data.get("answers", {})
        template_id = data.get("template_id")
        
        if not invitation_type or not event_type:
            return ResponseService.response("BAD_REQUEST", {"detail": "invitation_type and event_type are required."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        template = None
        if template_id:
            try:
                template = InvitationTemplate.objects.get(id=template_id)
            except InvitationTemplate.DoesNotExist:
                return ResponseService.response("BAD_REQUEST", {"detail": "Template not found."}, "Validation error", status.HTTP_400_BAD_REQUEST)
                
        invitation = Invitation.objects.create(
            user=user,
            invitation_type=invitation_type,
            event_type=event_type,
            template=template,
            answers=answers
        )
        return ResponseService.response("SUCCESS", {"id": invitation.id}, "Invitation created successfully.", status.HTTP_201_CREATED)

@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def invitation_detail_view(request: Request, invitation_id: int) -> Response:
    try:
        invitation = Invitation.objects.get(id=invitation_id, user=request.user)
    except Invitation.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Invitation not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        payload = {
            "id": invitation.id,
            "invitation_type": invitation.invitation_type,
            "event_type": invitation.event_type,
            "answers": invitation.answers,
            "template_id": invitation.template_id
        }
        return ResponseService.response("SUCCESS", payload, "Invitation retrieved successfully.")

    elif request.method == "DELETE":
        invitation.delete()
        return ResponseService.response("SUCCESS", {}, "Invitation deleted.", status.HTTP_204_NO_CONTENT)
