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
from django.http import JsonResponse, HttpResponse
from django.urls import path

from vendly_backend.controllers.admin_controller import (
    block_user,
    change_vendor_status,
    change_user_status,
    list_vendors,
    retrieve_user,
    retrieve_vendor,
    unblock_user,
    update_user,
    users_view,
)
from vendly_backend.controllers.admin_bookings_controller import (
    admin_bookings_list_view,
    admin_booking_update_view,
)
from vendly_backend.controllers.admin_dashboard_controller import (
    admin_best_performers_view,
    admin_dashboard_summary_view,
)
from vendly_backend.controllers.admin_activity_controller import (
    admin_activity_logs_view,
    admin_notifications_activity_view,
    admin_notification_activity_update_view,
)
from vendly_backend.controllers.admin_categories_controller import (
    admin_categories_view,
    admin_category_detail_view,
)
from vendly_backend.controllers.admin_template_types_controller import (
    admin_template_type_detail_view,
    admin_template_types_view,
    template_types_public_view,
)
from vendly_backend.controllers.admin_plans_controller import (
    admin_plans_view,
    admin_plan_detail_view,
)
from vendly_backend.controllers.auth_controller import (
    admin_login_view,
    confirm_registration_otp,
    login_view,
    logout_view,
    my_profile_view,
    register_customer,
    register_vendor,
)
from vendly_backend.controllers.vendor_controller import (
    public_vendor_detail_view,
    public_vendors_list_view,
    vendor_profile_view,
)
from vendly_backend.controllers.feed_controller import list_posts, toggle_feed_like, post_comments, comment_like, vendor_follow
from vendly_backend.controllers.bookings_controller import (
    booking_detail_view,
    booking_status_change_view,
    bookings_list_view,
)
from vendly_backend.controllers.reviews_controller import vendor_reviews_view
from vendly_backend.controllers.messaging_controller import (
    admin_chat_report_update_view,
    admin_chat_reports_view,
    conversation_detail_view,
    conversations_view,
    messages_view,
    read_messages_view,
    report_chat_messages_view,
    message_detail_view,
)

from vendly_backend.controllers.invitations_controller import invitation_templates_view, invitations_view, invitation_detail_view
from vendly_backend.controllers.categories_controller import categories_list_view, category_detail_view
from vendly_backend.controllers.favorites_controller import favorites_list_view, favorite_vendor_view
from vendly_backend.controllers.vendor_listings_controller import vendor_listings_view, vendor_listing_detail_view
from vendly_backend.controllers.vendor_posts_controller import (
    posts_collection_view,
    posts_detail_view,
    vendor_post_create_view,
    vendor_posts_view,
    vendor_post_detail_view,
    vendor_posts_by_vendor_id_view,
)
from vendly_backend.controllers.vendor_packages_controller import vendor_packages_view, vendor_package_detail_view, vendor_public_packages_view
from vendly_backend.controllers.vendor_subscriptions_controller import vendor_subscription_view, subscription_plans_view, activate_subscription_view
from vendly_backend.controllers.vendor_analytics_controller import vendor_analytics_view
from vendly_backend.controllers.vendor_calendar_controller import (
    vendor_calendar_view,
    vendor_availability_update_view,
)
from vendly_backend.controllers.notifications_controller import notifications_view, read_notification_view, notification_settings_view


def root_health_view(_request):
    return JsonResponse({"status": "ok", "service": "vendly_backend"}, status=200)


def favicon_view(_request):
    # Return empty success so browser favicon probes do not create noisy 404 logs.
    return HttpResponse(status=204)


urlpatterns = [
    path("", root_health_view, name="root_health"),
    path("favicon.ico", favicon_view, name="favicon"),
    path("admin/", admin.site.urls),
    # Auth
    path("api/admin/login", admin_login_view, name="admin_login"),
    path("api/admin/my-profile", my_profile_view, name="admin_my_profile"),
    # Both register views create the user then call _send_registration_otp (static OTP in cache; no SMS).
    path("api/auth/register/customer", register_customer, name="register_customer"),
    path("api/auth/register/vendor", register_vendor, name="register_vendor"),
    path("api/auth/confirm-otp", confirm_registration_otp, name="confirm_registration_otp"),
    path("api/auth/login", login_view, name="login"),
    path("api/auth/my-profile", my_profile_view, name="my_profile"),
    path("api/users/<int:path_user_id>", users_view, name="users_detail"),
    path("api/users", users_view, name="users"),
    path("api/auth/logout", logout_view, name="logout"),
    
    # Profile / Vendor Self-Service
    path("api/vendor/profile", vendor_profile_view, name="vendor_profile"),

    # Feed & Comments
    path("api/feed/posts", list_posts),
    path("api/feed/posts/<int:post_id>/like", toggle_feed_like),
    path("api/feed/posts/<int:post_id>/comments", post_comments),
    path("api/feed/comments/<int:comment_id>/like", comment_like),

    # Search & Categories
    path("api/categories", categories_list_view),
    path("api/categories/<int:category_id>", category_detail_view),
    
    # Favorites
    path("api/users/favorites", favorites_list_view),
    # Public vendor directory (GET list/detail; DELETE detail is admin-only)
    path("api/vendors", public_vendors_list_view),
    path("api/vendors/<int:vendor_id>", public_vendor_detail_view),
    path("api/vendors/<int:vendor_id>/favorite", favorite_vendor_view),
    path("api/vendors/<int:vendor_id>/follow", vendor_follow),

    # Bookings
    path("api/bookings", bookings_list_view),
    path("api/bookings/<int:booking_id>/status", booking_status_change_view),
    path("api/bookings/<int:booking_id>", booking_detail_view),

    # Reviews & Calendar
    path("api/vendors/<int:vendor_id>/calendar", vendor_calendar_view),
    path("api/vendor/availability", vendor_availability_update_view),
    path("api/vendors/<int:vendor_id>/reviews", vendor_reviews_view),
    path("api/vendors/<int:vendor_id>/posts", vendor_posts_by_vendor_id_view),

    # Messaging
    path("api/conversations", conversations_view),
    path("api/conversations/<int:conversation_id>", conversation_detail_view),
    path("api/conversations/<int:conversation_id>/messages", messages_view),
    path("api/conversations/<int:conversation_id>/read", read_messages_view),
    path("api/conversations/<int:conversation_id>/report", report_chat_messages_view),
    path("api/messages/<int:message_id>", message_detail_view),


    # Invitations
    path("api/invitations/templates", invitation_templates_view),
    path("api/invitations/template-types", template_types_public_view),
    path("api/invitations", invitations_view),
    path("api/invitations/<int:invitation_id>", invitation_detail_view),

    # Vendor - Listings (self)
    path("api/vendor/listings", vendor_listings_view),
    path("api/vendor/listings/<int:listing_id>", vendor_listing_detail_view),

    # Vendor - Posts (self); JSON or multipart (caption + media_file[s])
    path("api/vendor/posts", vendor_posts_view),
    path("api/posts/create", vendor_post_create_view),
    path("api/posts", posts_collection_view),
    path("api/posts/<int:post_id>", posts_detail_view),
    path("api/vendor/posts/<int:post_id>", vendor_post_detail_view),

    # Vendor - Packages & Subs (Public + Self)
    path("api/vendors/<int:vendor_id>/packages", vendor_public_packages_view),  # public by vendor_id
    path("api/vendor/packages", vendor_packages_view),                          # self (logged-in vendor)
    path("api/vendor/packages/<int:package_id>", vendor_package_detail_view),   # self (logged-in vendor)
    path("api/vendor/subscription", vendor_subscription_view, name="vendor_subscription"),
    path("api/vendor/subscription/activate", activate_subscription_view, name="activate_subscription"),
    path("api/subscription/plans", subscription_plans_view),

    # Vendor - Analytics (self)
    path("api/vendor/analytics", vendor_analytics_view),

    # Notifications
    path("api/users/notifications", notifications_view),
    path("api/users/notifications/<int:notification_id>/read", read_notification_view),
    path("api/users/notification-settings", notification_settings_view),

    # Admin: users
    path("api/admin/users/<int:user_id>", retrieve_user, name="admin_retrieve_user"),
    path("api/admin/users/<int:user_id>/update", update_user, name="admin_update_user"),
    path("api/admin/users-change-status", change_user_status, name="admin_users_change_status"),
    # Admin: vendors
    path("api/admin/vendors", list_vendors, name="admin_list_vendors"),
    path("api/admin/vendors/<int:vendor_id>", retrieve_vendor, name="admin_retrieve_vendor"),
    path("api/admin/vendors-change-status", change_vendor_status, name="admin_vendors_change_status"),

    # Admin: bookings
    path("api/admin/bookings", admin_bookings_list_view, name="admin_list_bookings"),
    path("api/admin/bookings/<int:booking_id>", admin_booking_update_view, name="admin_update_booking"),

    # Admin: dashboard
    path("api/admin/dashboard/summary", admin_dashboard_summary_view, name="admin_dashboard_summary"),
    path("api/admin/dashboard/best-performers", admin_best_performers_view, name="admin_best_performers"),

    # Admin: activity log (notifications seen/unseen)
    path("api/admin/activity/logs", admin_activity_logs_view, name="admin_activity_logs"),
    path("api/admin/activity/notifications", admin_notifications_activity_view, name="admin_activity_notifications"),
    path(
        "api/admin/activity/notifications/<int:notification_id>",
        admin_notification_activity_update_view,
        name="admin_activity_notification_update",
    ),

    # Admin: categories (list + create, detail + update + delete)
    path("api/admin/categories", admin_categories_view, name="admin_categories"),
    path(
        "api/admin/categories/<int:category_id>",
        admin_category_detail_view,
        name="admin_category_detail",
    ),
    # Admin: chat reports
    path("api/admin/chat-reports", admin_chat_reports_view, name="admin_chat_reports"),
    path("api/admin/chat-reports/<int:report_id>", admin_chat_report_update_view, name="admin_chat_report_update"),
    # Admin: invitation template types
    path("api/admin/template-types", admin_template_types_view, name="admin_template_types"),
    path("api/admin/template-types/<int:type_id>", admin_template_type_detail_view, name="admin_template_type_detail"),
    # Admin: subscription plans
    path("api/admin/plans", admin_plans_view, name="admin_plans"),
    path("api/admin/plans/<int:plan_id>", admin_plan_detail_view, name="admin_plan_detail"),
]
