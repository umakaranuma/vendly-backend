from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import VendorPackage, Vendor
from vendly_backend.permissions import IsVendor

@api_view(["GET"])
@permission_classes([AllowAny])
def vendor_public_packages_view(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Vendor not found.", status.HTTP_404_NOT_FOUND)

    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        
        query = (
            QueryBuilderService("vendor_packages")
            .select("vendor_packages.id", "vendor_packages.name", "vendor_packages.price", "vendor_packages.features_text", "vendor_packages.features_json", "vendor_packages.is_active")
            .apply_conditions(f'{{"vendor_id": {vendor.id}, "is_active": true}}', ["vendor_id", "is_active"], "", [])
            .paginate(page, limit, ["vendor_packages.created_at"], "vendor_packages.created_at", "asc")
        )
        return ResponseService.response("SUCCESS", query, "Vendor packages retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsVendor])
def vendor_packages_view(request: Request) -> Response:
    vendor = request.user.vendor
    
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            
            query = (
                QueryBuilderService("vendor_packages")
                .select("vendor_packages.id", "vendor_packages.name", "vendor_packages.price", "vendor_packages.features_text", "vendor_packages.features_json", "vendor_packages.is_active")
                .apply_conditions(f'{{"vendor_id": {vendor.id}}}', ["vendor_id"], "", [])
                .paginate(page, limit, ["vendor_packages.created_at"], "vendor_packages.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Packages retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        data = request.data
        name = data.get("name")
        price = data.get("price")
        features_text = data.get("features_text", "")
        features_json = data.get("features_json")
        is_active = data.get("is_active", True)
        
        if not name or price is None:
            return ResponseService.response("BAD_REQUEST", {"detail": "Name and price are required."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        # Business Rule: Check max_packages limit
        # active_subscriptions = vendor.subscriptions.filter(is_active=True).select_related('plan').first()
        # max_allowed = active_subscriptions.plan.max_packages if active_subscriptions else 2
        
        # current_count = VendorPackage.objects.filter(vendor=vendor, is_active=True).count()
        # if current_count >= max_allowed:
        #    return ResponseService.response("FORBIDDEN", {"detail": f"Package limit reached ({max_allowed})."}, "Validation error", status.HTTP_403_FORBIDDEN)
            
        package = VendorPackage.objects.create(
            vendor=vendor,
            name=name,
            price=price,
            features_text=features_text,
            features_json=features_json,
            is_active=is_active
        )
        
        payload = {
            "id": package.id,
            "name": package.name,
            "price": str(package.price),
            "is_active": package.is_active
        }
        return ResponseService.response("SUCCESS", payload, "Package created successfully.", status.HTTP_201_CREATED)

@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated, IsVendor])
def vendor_package_detail_view(request: Request, package_id: int) -> Response:
    try:
        package = VendorPackage.objects.get(id=package_id, vendor=request.user.vendor)
    except VendorPackage.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Package not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "PUT":
        data = request.data
        
        if "name" in data:
            package.name = data.get("name")
        if "price" in data:
            package.price = data.get("price")
        if "features_text" in data:
            package.features_text = data.get("features_text")
        if "features_json" in data:
            package.features_json = data.get("features_json")
        if "is_active" in data:
            package.is_active = data.get("is_active")
            
        package.save()
        
        payload = {
            "id": package.id,
            "name": package.name,
            "price": str(package.price),
            "is_active": package.is_active
        }
        return ResponseService.response("SUCCESS", payload, "Package updated successfully.")

    elif request.method == "DELETE":
        package.delete()
        return ResponseService.response("SUCCESS", {}, "Package deleted.", status.HTTP_204_NO_CONTENT)
