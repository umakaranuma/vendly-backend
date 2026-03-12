"""
URL configuration for vendly_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from vendly_backend.controllers.admin_controller import (
    approve_vendor,
    block_user,
    list_users,
    list_vendors,
    reject_vendor,
    retrieve_user,
    retrieve_vendor,
    unblock_user,
    update_user,
)
from vendly_backend.controllers.auth_controller import (
    login_view,
    logout_view,
    me_view,
    register_customer,
    register_vendor,
)
from vendly_backend.controllers.vendor_controller import vendor_profile_view

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path("api/auth/register/customer/", register_customer, name="register_customer"),
    path("api/auth/register/vendor/", register_vendor, name="register_vendor"),
    path("api/auth/login/", login_view, name="login"),
    path("api/auth/me/", me_view, name="me"),
    path("api/auth/logout/", logout_view, name="logout"),
    # Vendor self-service
    path("api/vendor/profile/", vendor_profile_view, name="vendor_profile"),
    # Admin: users
    path("api/admin/users/", list_users, name="admin_list_users"),
    path("api/admin/users/<int:user_id>/", retrieve_user, name="admin_retrieve_user"),
    path("api/admin/users/<int:user_id>/update/", update_user, name="admin_update_user"),
    path("api/admin/users/<int:user_id>/block/", block_user, name="admin_block_user"),
    path("api/admin/users/<int:user_id>/unblock/", unblock_user, name="admin_unblock_user"),
    # Admin: vendors
    path("api/admin/vendors/", list_vendors, name="admin_list_vendors"),
    path("api/admin/vendors/<int:vendor_id>/", retrieve_vendor, name="admin_retrieve_vendor"),
    path("api/admin/vendors/<int:vendor_id>/approve/", approve_vendor, name="admin_approve_vendor"),
    path("api/admin/vendors/<int:vendor_id>/reject/", reject_vendor, name="admin_reject_vendor"),
]
