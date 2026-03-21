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
| GET | `/api/admin/activity/notifications` | Admin activity notifications |
| PATCH | `/api/admin/activity/notifications/<notification_id>` | Update activity notification |
| POST | `/api/admin/categories` | Create category (admin) |

---

## 14. Django admin site (browser)

| Method(s) | Path | Description |
|-----------|------|-------------|
| * | `/admin/` | Django `admin.site` UI (staff/superuser) |

---

*To update this document, edit routes in `vendly_backend/urls.py` and mirror HTTP methods from each view’s `@api_view([...])`.*
