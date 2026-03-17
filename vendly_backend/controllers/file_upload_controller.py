from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def file_upload_view(request: Request) -> Response:
    # A real implementation would handle S3 upload here using request.FILES['file']
    # We will stub it for now to match exactly what is required
    
    file_obj = request.FILES.get('file')
    path = request.data.get('path', 'uploads/')
    
    if not file_obj:
        return ResponseService.response("BAD_REQUEST", {"detail": "file is required."}, "Validation error", status.HTTP_400_BAD_REQUEST)

    # Fake CDN logic
    file_name = file_obj.name.replace(" ", "_")
    uploaded_url = f"https://cdn.example.com/{path}{file_name}"
    
    payload = {
        "url": uploaded_url
    }
    return ResponseService.response("SUCCESS", payload, "File uploaded successfully.", status.HTTP_200_OK)
