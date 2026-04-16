import os
import json
import re
import requests
import urllib.parse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import InvitationTemplate, Invitation

def _extract_json(raw_text):
    trimmed = raw_text.strip()
    
    # Try direct parse
    try:
        return json.loads(trimmed)
    except:
        pass
        
    # Strip markdown fences
    fence_re = re.compile(r'```(?:json)?\s*([\s\S]*?)\s*```')
    match = fence_re.search(trimmed)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
            
    # Find first { ... }
    start = trimmed.find('{')
    end = trimmed.rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(trimmed[start:end+1])
        except:
            pass
            
    return {}

def _build_gemini_prompt(event_type, answers):
    buffer = [
        f"You are an expert invitation writer. Generate beautiful, heartfelt, and elegant invitation text for a {event_type}.",
        "Return a JSON object with EXACTLY these keys:",
        "  headline, subheadline, body, closing_line, tagline",
        "Rules:",
        "- headline: 4-8 words, poetic opener (e.g. \"Two hearts, one forever\")",
        "- subheadline: the event/couple name formatted nicely (e.g. \"John & Jane's Wedding\")",
        "- body: 2-3 sentences, warm formal invitation text using the names, venue, and date",
        "- closing_line: warm sign-off (e.g. \"With love, The Silvas\")",
        "- tagline: 5-10 words, short catchy phrase (e.g. \"Join us as we celebrate love\")",
        "- Do NOT invent details not provided below.",
        "- Return ONLY the raw JSON object. No markdown, no explanation, no code fences.",
        "",
        "Event details:",
        f"- Event type: {event_type}"
    ]
    
    for key, value in answers.items():
        if value and str(value).strip():
            display_key = key.replace('_', ' ')
            buffer.append(f"- {display_key}: {value}")
            
    return "\n".join(buffer)

def _build_image_prompt(event_type, json_data):
    """
    Builds a prompt for AI image generation (e.g. Pollinations.ai)
    """
    headline = json_data.get("headline", "")
    tagline = json_data.get("tagline", "")
    
    # Create a descriptive prompt for the background art
    # We want it to be artistic but leaving room for text in the middle
    prompt = f"Professional luxury {event_type} invitation card background, {tagline}, {headline}, elegant, detailed, high resolution, centered composition with space for text, high-end design"
    
    return urllib.parse.quote(prompt)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_invitation_content_view(request: Request) -> Response:
    try:
        data = request.data
        event_type = data.get("event_type", "Other event")
        answers = data.get("answers", {})

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"detail": "Gemini API key not configured on server (or empty)."}, "Config error")

        prompt = _build_gemini_prompt(event_type, answers)
        
        # List of models to try in order of likelihood of success/quota availability
        # gemini-3.1-flash-lite-preview was verified as working in 2026 logs.
        models = [
            "gemini-3.1-flash-lite-preview",
            "gemini-2.0-flash",
            "gemini-flash-latest"
        ]
        
        last_error = None
        raw_text = None
        
        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.85,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 1024,
                    }
                }
                
                response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if raw_text:
                            break # Found success!
                    
                    last_error = "Empty AI response"
                elif response.status_code == 429:
                    last_error = f"Model {model} over quota (429)"
                    continue # Try next model
                else:
                    last_error = f"Gemini API error ({response.status_code}): {response.text[:100]}"
                    continue # Try next model
            except Exception as e:
                last_error = f"Request error for {model}: {str(e)}"
                continue

        if not raw_text:
            msg = "AI services are currently busy or at capacity. Please try again in a few minutes or fill the template manually."
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"detail": last_error}, msg)

        json_data = _extract_json(raw_text)
        if not json_data:
             return ResponseService.response("INTERNAL_SERVER_ERROR", {"detail": "Failed to parse AI structure."}, "AI formatting error")
        
        # Add a generated background image URL
        image_prompt = _build_image_prompt(event_type, json_data)
        # Use Pollinations.ai for free, fast AI images
        json_data["background_image_url"] = f"https://image.pollinations.ai/prompt/{image_prompt}?width=1024&height=1024&nologo=true&enhance=true"
             
        return ResponseService.response("SUCCESS", json_data, "Content generated successfully.")

    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

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
        ai_content = data.get("ai_content")
        template_id = data.get("template_id")
        
        # Merge AI content into answers for storage
        if ai_content:
            answers["ai_content"] = ai_content
            
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
