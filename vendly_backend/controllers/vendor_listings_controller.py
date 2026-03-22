from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import Listing
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def vendor_listings_view(request: Request) -> Response:
    vendor = request.user.vendor
    
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            query = (
                QueryBuilderService("listings")
                .select("listings.id", "listings.title", "listings.description", "listings.price", "listings.category", "listings.created_at")
                .apply_conditions(f'{{"vendor_id": {vendor.id}}}', ["vendor_id"], "", [])
                .paginate(page, limit, ["listings.created_at"], "listings.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Listings retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        data = request.data
        title = data.get("title")
        description = data.get("description", "")
        price = data.get("price")
        category = data.get("category", "")
        
        if not title:
            return ResponseService.response("BAD_REQUEST", {"detail": "Title is required."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        listing = Listing.objects.create(
            vendor=vendor,
            title=title,
            description=description,
            price=price,
            category=category
        )
        
        payload = {
            "id": listing.id,
            "title": listing.title,
            "description": listing.description,
            "price": str(listing.price) if listing.price else None,
            "category": listing.category
        }
        return ResponseService.response("SUCCESS", payload, "Listing created successfully.", status.HTTP_201_CREATED)

@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def vendor_listing_detail_view(request: Request, listing_id: int) -> Response:
    try:
        listing = Listing.objects.get(id=listing_id, vendor=request.user.vendor)
    except Listing.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Listing not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "PUT":
        data = request.data
        
        if "title" in data:
            listing.title = data.get("title")
        if "description" in data:
            listing.description = data.get("description")
        if "price" in data:
            listing.price = data.get("price")
        if "category" in data:
            listing.category = data.get("category")
            
        listing.save()
        
        payload = {
            "id": listing.id,
            "title": listing.title,
            "description": listing.description,
            "price": str(listing.price) if listing.price else None,
            "category": listing.category
        }
        return ResponseService.response("SUCCESS", payload, "Listing updated successfully.")

    elif request.method == "DELETE":
        listing.delete()
        return ResponseService.response("SUCCESS", {}, "Listing deleted.", status.HTTP_204_NO_CONTENT)
