# Vendly Backend — API endpoints

Reference generated from `vendly_backend/urls.py` and `@api_view` decorators on the corresponding views.  
Prefix all paths with your server origin (e.g. `https://api.example.com/`).  
Authenticated routes expect `Authorization: Bearer <access_token>` unless noted.

---

## 1. Authentication & users (login, register, OTP, logout)

| Method(s) | Path | Description |
|-----------|------|-------------|
| POST | `/api/auth/register/customer` | Register customer |
| POST | `/api/auth/register/vendor` | Register vendor |
| POST | `/api/auth/confirm-otp` | Confirm registration OTP |
| POST | `/api/auth/login` | Login (email or phone + password) |
| POST | `/api/auth/logout` | Logout (optional refresh body) |
| POST | `/api/admin/login` | Admin JWT login (role `ADMIN`/`SUPER_ADMIN`, or Django superuser; same body as login) |
| GET, PATCH | `/api/users` | List/filter users (GET) or update profile (PATCH) |

### 1.1 `/api/users` response reference

#### `GET /api/users` (admin user)

Admin list response is paginated and returned through `ResponseService`.

```json
{
  "is_success": true,
  "message": "Users fetched successfully.",
  "result": {
    "total_records": 1,
    "per_page": 20,
    "current_page": 1,
    "last_page": 1,
    "data": [
      {
        "id": 7,
        "email": "user@example.com",
        "phone": "+919999999999",
        "first_name": "Test",
        "last_name": "User",
        "is_active": true,
        "is_verified": true,
        "role_id": 2,
        "role_name": "CUSTOMER",
        "role_description": "",
        "status": "active"
      }
    ]
  },
  "system_code": 200
}
```

#### `GET /api/users` (non-admin user)

Returns the authenticated user's profile object.

```json
{
  "is_success": true,
  "message": "User fetched successfully.",
  "result": {
    "id": 7,
    "email": "user@example.com",
    "phone": "+919999999999",
    "first_name": "Test",
    "last_name": "User",
    "is_active": true,
    "is_verified": true,
    "status": "active",
    "role": {
      "id": 2,
      "name": "CUSTOMER",
      "description": ""
    }
  },
  "system_code": 200
}
```

---

## 2. Profile & vendor self-service

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET, PATCH | `/api/vendor/profile` | Vendor profile (vendor role) |

---

## 3. Feed & comments

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET | `/api/feed/posts` | List feed posts |
| POST, DELETE | `/api/feed/posts/<post_id>/like` | Like / unlike post |
| GET, POST | `/api/feed/posts/<post_id>/comments` | List / add comments |
| POST | `/api/feed/comments/<comment_id>/like` | Like comment |

---

## 4. Categories

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET | `/api/categories` | List categories |
| GET | `/api/categories/<category_id>` | Category detail |

---

## 5. Favorites

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET | `/api/users/favorites` | List favorites |
| POST, DELETE | `/api/vendors/<vendor_id>/favorite` | Add / remove favorite |

---

## 6. Bookings

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET, POST | `/api/bookings` | List / create bookings |
| GET, PATCH | `/api/bookings/<booking_id>` | Booking detail / update |

---

## 7. Reviews

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET, POST | `/api/vendors/<vendor_id>/reviews` | List / create reviews |

---

## 8. Messaging

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET, POST | `/api/conversations` | List / create conversations |
| GET, DELETE | `/api/conversations/<conversation_id>` | Detail / delete conversation |
| GET, POST | `/api/conversations/<conversation_id>/messages` | List / send messages |
| PATCH | `/api/conversations/<conversation_id>/read` | Mark as read |
| POST | `/api/conversations/<conversation_id>/report` | Report up to 5 chat messages |

---

## 9. Invitations

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET | `/api/invitations/templates` | Invitation templates |
| GET, POST | `/api/invitations` | List / create invitations |
| GET, DELETE | `/api/invitations/<invitation_id>` | Detail / delete invitation |

---

## 10. Vendor — listings, posts, packages, subscription, analytics

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET, POST | `/api/vendor/listings` | Vendor listings |
| PUT, DELETE | `/api/vendor/listings/<listing_id>` | Update / delete listing |
| GET, POST | `/api/vendor/posts` | Vendor posts |
| DELETE | `/api/vendor/posts/<post_id>` | Delete post |
| GET | `/api/vendors/<vendor_id>/packages` | Public packages by vendor |
| GET, POST | `/api/vendor/packages` | Logged-in vendor packages |
| PUT, DELETE | `/api/vendor/packages/<package_id>` | Update / delete package |
| GET | `/api/vendor/subscription` | Vendor subscription |
| GET | `/api/subscription/plans` | Subscription plans |
| GET | `/api/vendor/analytics` | Vendor analytics |

---

## 11. Notifications

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET | `/api/users/notifications` | List notifications |
| PATCH | `/api/users/notifications/<notification_id>/read` | Mark notification read |
| PATCH | `/api/users/notification-settings` | Notification settings |

---

## 12. File upload

| Method(s) | Path | Description |
|-----------|------|-------------|
| POST | `/api/upload-file` | Upload file |

---

## 13. Admin API

| Method(s) | Path | Description |
|-----------|------|-------------|
| GET | `/api/admin/users/<user_id>` | Retrieve user |
| PATCH | `/api/admin/users/<user_id>/update` | Update user |
| POST | `/api/admin/users-change-status` | Change user status |
| GET | `/api/admin/vendors` | List vendors |
| GET | `/api/admin/vendors/<vendor_id>` | Retrieve vendor |
| POST | `/api/admin/vendors-change-status` | Change vendor status |
| GET | `/api/admin/bookings` | List bookings (admin) |
| PATCH | `/api/admin/bookings/<booking_id>` | Update booking (admin) |
| GET | `/api/admin/dashboard/summary` | Dashboard summary |
| GET | `/api/admin/dashboard/best-performers` | Month-wise best performers (vendors) |
| GET | `/api/admin/activity/logs` | Admin activity logs |
| GET | `/api/admin/activity/notifications` | Admin activity notifications |
| PATCH | `/api/admin/activity/notifications/<notification_id>` | Update activity notification |
| POST | `/api/admin/categories` | Create category (admin) |
| GET, POST | `/api/admin/template-types` | Template types list/create (admin) |
| GET, PATCH, DELETE | `/api/admin/template-types/<type_id>` | Template type detail/update/delete (admin) |
| GET | `/api/admin/chat-reports` | Chat reports list (admin) |
| PATCH | `/api/admin/chat-reports/<report_id>` | Chat report status/action update (admin) |

### 13.1 Admin chat reports payload reference

#### `GET /api/admin/chat-reports`

**Query params (optional):**
- `page` (int, default: `1`)
- `limit` (int, default: `20`)
- `conversation_id` (int)
- `reporter_id` (int)
- `status` (string like `open`, `in_review`, etc.; validated using `core_statuses` as `chat_report_<status>`)
- `reason_type` (string/free text)

**Success response format:**

```json
{
  "is_success": true,
  "message": "Chat reports retrieved successfully.",
  "result": {
    "total_records": 1,
    "per_page": 20,
    "current_page": 1,
    "last_page": 1,
    "data": [
      {
        "id": 12,
        "conversation_id": 44,
        "reporter_id": 9,
        "reason_type": "harassment",
        "reason": "Abusive words in chat",
        "status_id": 101,
        "status": "open",
        "status_type": "chat_report_open",
        "admin_action_note": null,
        "reviewed_by_id": null,
        "reviewed_at": null,
        "created_at": "2026-03-21T12:10:00Z",
        "reporter_first_name": "Arun",
        "reporter_last_name": "K",
        "reporter_role": "CUSTOMER",
        "reported_messages": [
          {
            "message_id": 501,
            "chat_id": 44,
            "text": "Sample abusive message",
            "attachment_url": null,
            "message_created_at": "2026-03-21T11:58:00Z",
            "sender_id": 22,
            "sender_type": "vendor",
            "sender_first_name": "Vendor",
            "sender_last_name": "One"
          }
        ]
      }
    ]
  },
  "system_code": 200
}
```

#### `PATCH /api/admin/chat-reports/<report_id>`

**Request body (at least one field required):**

```json
{
  "status": "in_review",
  "admin_action_note": "Warned vendor account and monitoring next messages."
}
```

**Success response format:**

```json
{
  "is_success": true,
  "message": "Chat report updated successfully.",
  "result": {
    "id": 12,
    "status": "in_review",
    "status_type": "chat_report_in_review",
    "status_id": 102,
    "admin_action_note": "Warned vendor account and monitoring next messages.",
    "reviewed_by_id": 1,
    "reviewed_at": "2026-03-21T12:20:00Z"
  },
  "system_code": 200
}
```

### 13.2 Template types response reference

#### `GET /api/admin/template-types` and `GET /api/invitations/template-types`

Both endpoints are paginated and returned via `ResponseService`.

```json
{
  "is_success": true,
  "message": "Template types retrieved successfully.",
  "result": {
    "total_records": 1,
    "per_page": 20,
    "current_page": 1,
    "last_page": 1,
    "data": [
      {
        "id": 1,
        "name": "Video",
        "type_key": "template_video",
        "description": "Video invitation template type",
        "sort_order": 10
      }
    ]
  },
  "system_code": 200
}
```

---

## 14. Django admin site (browser)

| Method(s) | Path | Description |
|-----------|------|-------------|
| * | `/admin/` | Django `admin.site` UI (staff/superuser) |

---

*To update this document, edit routes in `vendly_backend/urls.py` and mirror HTTP methods from each view’s `@api_view([...])`.*
