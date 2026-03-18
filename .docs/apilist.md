# Vendly Mobile – API Endpoint Reference

> Complete list of all recommended REST API endpoints for the Vendly Mobile backend.
> Auth endpoints use the **IDP base URL**; all other endpoints use the **Main API base URL**.
> All authenticated endpoints require `Authorization: Bearer <token>` header.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Profile](#2-profile)
3. [Feed & Comments](#3-feed--comments)
4. [Search & Vendors](#4-search--vendors)
5. [Categories](#5-categories)
6. [Favorites](#6-favorites)
7. [Bookings](#7-bookings)
8. [Vendor Reviews](#8-vendor-reviews)
9. [Messages & Chat](#9-messages--chat)
10. [Invitations](#10-invitations)
11. [Vendor – Listings](#11-vendor--listings)
12. [Vendor – Posts](#12-vendor--posts)
13. [Vendor – Packages](#13-vendor--packages)
14. [Vendor – Subscription](#14-vendor--subscription)
15. [Vendor – Analytics](#15-vendor--analytics)
16. [Notifications](#16-notifications)
17. [Admin](#17-admin)
18. [File Upload](#18-file-upload)

---

## 1. Authentication

> Base: IDP URL (`idpBaseUrl`)

| Method | Path | Auth | Request Body | Response | Notes |
|---|---|---|---|---|---|
| POST | `auth/register` | None | `{ name, email, password, role: "customer"\|"vendor" }` | `{ is_success, message, result: { user, token } }` | Creates user account |
| POST | `auth/login` | None | `{ email, password }` | `{ is_success, message, result: { user, token } }` | Returns Bearer token |
| POST | `auth/logout` | Bearer | — | 204 | Invalidates token |
| POST | `auth/forgot-password` | None | `{ email }` | `{ message }` | Password reset flow |

---

## 2. Profile

| Method | Path | Auth | Request / Query | Response | Notes |
|---|---|---|---|---|---|
| GET | `users/me` | Bearer | — | `User` (id, name, email, avatar_url, cover_url, bio, role) | Current user profile |
| PUT | `users/me` | Bearer | `{ name?, avatar_url?, cover_url?, bio? }` | Updated `User` | Edit profile |

---

## 3. Feed & Comments

| Method | Path | Auth | Request / Query | Response | Notes |
|---|---|---|---|---|---|
| GET | `feed/posts` | Bearer | `?page=1&limit=20` | `{ items: [FeedPost], next_page? }` | Paginated feed |
| POST | `feed/posts/:id/like` | Bearer | — | `{ liked, like_count }` | Like a post |
| DELETE | `feed/posts/:id/like` | Bearer | — | 204 | Unlike a post |
| GET | `feed/posts/:id/comments` | Bearer | — | `{ comments: [FeedComment], total }` | List comments |
| POST | `feed/posts/:id/comments` | Bearer | `{ text, parent_id? }` | `FeedComment` | Add comment or reply |
| POST | `feed/comments/:id/like` | Bearer | — | 204 | Like a comment |

**FeedPost shape:** `id, vendor_id, media: [{ url, is_video }], caption, like_count, comment_count, created_at`

**FeedComment shape:** `id, author_name, author_avatar_url, text, time_ago, like_count, is_liked, replies: [FeedComment]`

---

## 4. Search & Vendors

| Method | Path | Auth | Query Params | Response | Notes |
|---|---|---|---|---|---|
| GET | `vendors` | Bearer | `q?, category_id?, category_slug?, min_price?, max_price?, page=1, limit=20` | `{ items: [Vendor], total }` | Returns approved vendors only |
| GET | `vendors/:id` | Bearer | — | `Vendor` (with gallery, services) | 404 if not approved |
| GET | `search/suggestions` | Bearer | `q=<string>` | `{ recent?: string[], categories?: Category[] }` | Search autocomplete |

**Vendor shape:** `id, name, city, category, rating, review_count, price_from, gallery: [url], bio, status`

---

## 5. Categories

| Method | Path | Auth | Request | Response | Who |
|---|---|---|---|---|---|
| GET | `categories` | Optional | `?page=1&limit=50` | `{ items: [Category], total }` | All |
| GET | `categories/:id` | Optional | — | `Category` | All |
| POST | `admin/categories` | Admin | `{ name, slug?, description?, sort_order? }` | `Category` | Admin only |
| PUT | `admin/categories/:id` | Admin | `{ name?, slug?, description?, sort_order? }` | `Category` | Admin only |
| DELETE | `admin/categories/:id` | Admin | — | 204 | Admin only |

**Category shape:** `id, name, slug, description, sort_order, created_at, updated_at`

---

## 6. Favorites

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `users/me/favorites` | Bearer | — | `{ items: [Vendor] }` | Liked vendors list |
| POST | `vendors/:id/favorite` | Bearer | — | 201 | Add to favorites |
| DELETE | `vendors/:id/favorite` | Bearer | — | 204 | Remove from favorites |

---

## 7. Bookings

| Method | Path | Auth | Request / Query | Response | Notes |
|---|---|---|---|---|---|
| GET | `bookings` | Bearer | `?status?, page=1, limit=20` | `{ items: [Booking], total }` | Customer: own bookings; Vendor: vendor's bookings |
| GET | `bookings/:id` | Bearer | — | `Booking` | Full booking detail |
| POST | `bookings` | Bearer | `{ vendor_id, event_type, booking_date, location, amount, deposit, message? }` | `Booking` | Create booking |
| PATCH | `bookings/:id` | Bearer | `{ status: "confirmed"\|"completed"\|"cancelled" }` | `Booking` | Update booking status |

**Booking shape:** `id, customer_id, vendor_id, event_type, booking_date, location, amount, deposit, status, created_at, updated_at`

**Status values:** `pending` → `confirmed` → `completed` | `cancelled`

---

## 8. Vendor Reviews

| Method | Path | Auth | Request / Query | Response | Who |
|---|---|---|---|---|---|
| GET | `vendors/:id/reviews` | Optional | `?page=1&limit=20` | `{ items: [Review], total, average_rating }` | All (approved vendors) |
| POST | `vendors/:id/reviews` | Bearer | `{ booking_id, rating, comment? }` | `Review` | Customer with completed booking only |
| DELETE | `admin/reviews/:id` | Admin | — | 204 | Admin only |

**Review shape:** `id, booking_id, reviewer_id, vendor_id, rating, comment, created_at`

**Business rule:** Backend validates that `bookings.customer_id = current_user`, `bookings.status = 'completed'`, and no existing review for that booking_id.

---

## 9. Messages & Chat

| Method | Path | Auth | Request / Query | Response | Notes |
|---|---|---|---|---|---|
| GET | `conversations` | Bearer | — | `{ items: [ConversationListItem], total }` | Conversations for current user |
| GET | `conversations/:id` | Bearer | — | `ConversationDetail` | Full conversation + participants |
| POST | `conversations` | Bearer | `{ partner_id? }` or `{ vendor_id? }` | `Conversation` (201 new, 200 existing) | Idempotent: returns existing if found |
| GET | `conversations/:id/messages` | Bearer | `?before=<message_id>&limit=20` | `{ items: [Message], has_more, next_cursor? }` | Cursor-based pagination |
| POST | `conversations/:id/messages` | Bearer | `{ text }` or multipart with `file` | `Message` | Send message or attachment |
| PATCH | `conversations/:id/read` | Bearer | — | 204 | Mark all messages as read |
| DELETE | `conversations/:id` | Bearer | — | 204 | Leave/archive conversation |

**ConversationListItem shape:** `id, participants: [{user_id, name, avatar_url, role}], last_message: {id, text, sender_id, created_at, sent_by_me}, unread_count, updated_at`

**Message shape:** `id, conversation_id, sender_id, text, attachment_url?, created_at, read_at?`

---

## 10. Invitations

| Method | Path | Auth | Request / Query | Response | Notes |
|---|---|---|---|---|---|
| GET | `invitations` | Bearer | `?page=1&limit=20` | `{ items: [Invitation], total }` | User's invitations |
| POST | `invitations` | Bearer | `{ invitation_type, event_type, answers: {key: value}, template_id? }` | `Invitation` | Create invitation |
| GET | `invitations/:id` | Bearer | — | `Invitation` (with template) | Invitation detail |
| DELETE | `invitations/:id` | Bearer | — | 204 | Delete invitation |
| GET | `invitations/templates` | Bearer | `?type=card\|video\|website` | `{ items: [InvitationTemplate] }` | Available templates |

**Invitation types:** `card`, `video`, `website`

**Event types:** `wedding`, `pubertyCeremony`, `householdFunction`, `birthday`, `engagement`, `other`

**InvitationTemplate shape:** `id, name, description, style, icon, invitation_type, sort_order`

---

## 11. Vendor – Listings

> Vendor-authenticated endpoints only.

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `vendors/me/listings` | Vendor | — | `{ items: [Listing] }` |
| POST | `vendors/me/listings` | Vendor | `{ title, description, price, category }` | `Listing` |
| PUT | `vendors/me/listings/:id` | Vendor | `{ title?, description?, price?, category? }` | `Listing` |
| DELETE | `vendors/me/listings/:id` | Vendor | — | 204 |

---

## 12. Vendor – Posts

> Vendor-authenticated endpoints only.

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `vendors/me/posts` | Vendor | — | `{ items: [Post] }` |
| POST | `vendors/me/posts` | Vendor | multipart or `{ caption, media: [{ url, is_video }] }` | `Post` |
| DELETE | `vendors/me/posts/:id` | Vendor | — | 204 |

---

## 13. Vendor – Packages

| Method | Path | Auth | Request | Response | Who |
|---|---|---|---|---|---|
| GET | `vendors/:vendor_id/packages` | Optional | — | `{ items: [VendorPackage] }` | All (approved vendors) |
| GET | `vendors/me/packages` | Vendor | — | `{ items: [VendorPackage] }` | Vendor (own) |
| POST | `vendors/me/packages` | Vendor | `{ name, price, features: string[]\|string, is_active? }` | `VendorPackage` | Subject to max_packages limit |
| PUT | `vendors/me/packages/:id` | Vendor | same as POST | `VendorPackage` | |
| DELETE | `vendors/me/packages/:id` | Vendor | — | 204 | |

**VendorPackage shape:** `id, vendor_id, name, price, features, is_active, created_at, updated_at`

---

## 14. Vendor – Subscription

| Method | Path | Auth | Request | Response | Who |
|---|---|---|---|---|---|
| GET | `vendors/me/subscription` | Vendor | — | `VendorSubscription` (plan, limits, expiry) | Vendor |
| GET | `subscription/plans` | Bearer | — | `{ items: [SubscriptionPlan] }` | Vendors/Admin |
| POST | `admin/subscription/plans` | Admin | `{ name, max_packages, price?, description? }` | `SubscriptionPlan` | Admin |
| PUT | `admin/subscription/plans/:id` | Admin | same | `SubscriptionPlan` | Admin |
| DELETE | `admin/subscription/plans/:id` | Admin | — | 204 | Admin |
| GET | `admin/vendors/:id/subscription` | Admin | — | `VendorSubscription` | Admin |
| POST | `admin/vendors/:id/subscription` | Admin | `{ plan_id, starts_at?, ends_at? }` | `VendorSubscription` | Admin (assign/upgrade) |

---

## 15. Vendor – Analytics

| Method | Path | Auth | Query | Response |
|---|---|---|---|---|
| GET | `vendors/me/analytics` | Vendor | `?from=<date>&to=<date>` | `{ views, likes, bookings_count, revenue, chart_data? }` |

---

## 16. Notifications

| Method | Path | Auth | Request / Query | Response |
|---|---|---|---|---|
| GET | `users/me/notifications` | Bearer | `?page=1&limit=20` | `{ items: [Notification], unread_count }` |
| PATCH | `users/me/notifications/:id/read` | Bearer | — | 204 |
| PATCH | `users/me/notification-settings` | Bearer | `{ push?, email?, ... }` | 200 |

---

## 17. Admin

> All admin endpoints require `role = admin`.

### Users
| Method | Path | Description |
|---|---|---|
| GET | `admin/users` | List users (paginated, filter by role) |
| GET | `admin/users/:id` | User detail |
| PATCH | `admin/users/:id` | Update user (role, suspend, etc.) |

### Vendors
| Method | Path | Description |
|---|---|---|
| GET | `admin/vendors` | List vendors; filter by `status` |
| PATCH | `admin/vendors/:id/approve` | Approve vendor (`status = 'approved'`) |
| PATCH | `admin/vendors/:id/reject` | Reject/suspend vendor |
| GET | `admin/vendors/:id/subscription` | View vendor's subscription |
| POST | `admin/vendors/:id/subscription` | Assign/upgrade vendor subscription |

### Content Moderation
| Method | Path | Description |
|---|---|---|
| GET | `admin/posts` | List all posts; filter by vendor |
| DELETE | `admin/posts/:id` | Delete post |
| GET | `admin/conversations` | List all conversations (paginated) |
| GET | `admin/conversations/:id/messages` | View messages in conversation |
| DELETE | `admin/messages/:id` | Delete message |
| DELETE | `admin/reviews/:id` | Delete vendor review |

### Categories
| Method | Path | Description |
|---|---|---|
| POST | `admin/categories` | Create category |
| PUT | `admin/categories/:id` | Update category |
| DELETE | `admin/categories/:id` | Delete category |

### Subscriptions
| Method | Path | Description |
|---|---|---|
| POST | `admin/subscription/plans` | Create subscription plan |
| PUT | `admin/subscription/plans/:id` | Update subscription plan |
| DELETE | `admin/subscription/plans/:id` | Delete subscription plan |

### Other
| Method | Path | Description |
|---|---|---|
| GET | `admin/bookings` | List all bookings |
| GET | `admin/invitations` | List all invitations |
| GET | `admin/notifications` | List or send system notifications |

---

## 18. File Upload

| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `upload-file` | Bearer | multipart: `file`, `path` (key/folder) | `{ url }` | Returns CDN/S3 URL. Used for avatars, covers, post media, attachments. |

---

## Response Envelope (Standard)

Most endpoints return a consistent response structure:

```json
{
  "is_success": true,
  "message": "...",
  "result": { ... },
  "system_code": "..."
}
```

List endpoints return:

```json
{
  "items": [ ... ],
  "total": 100,
  "next_page": 2
}
```

---

## HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | OK |
| 201 | Created |
| 204 | No Content (success, no body) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/expired token) |
| 403 | Forbidden (insufficient role) |
| 404 | Not Found |
| 409 | Conflict (e.g. duplicate unique constraint) |
| 500 | Internal Server Error |

---

*API reference generated from `FEATURES_APIS_AND_DATABASE.md`. Update when new endpoints are added or existing ones are modified.*

---

## Generated From `vendly_backend/urls.py` (Methods, Params, Payload)

### Auth
| Method | Endpoint | Auth | Query Params | Body (request data) |
|---|---|---|---|---|
| POST | `/api/auth/register/customer` | None | — | `email` (required, valid email), `phone` (required), `password` (required, min 6), `first_name` (required), `last_name` (optional) |
| POST | `/api/auth/register/vendor` | None | — | `email` (required), `phone` (required), `password` (required, min 6), `store_name` or `name` (required), `city` (optional), `first_name` (optional), `last_name` (optional) |
| POST | `/api/auth/login` | None | — | `password` (required), `email` (optional), `phone` (optional) (but at least one of `email`/`phone` must be provided) |
| GET | `/api/users/me` | Bearer | — | — |
| PATCH | `/api/users/me` | Bearer | — | `first_name` (optional), `last_name` (optional), `phone` (optional) |
| POST | `/api/auth/logout` | Bearer | — | `refresh` (optional) |

### Vendor Self-Service
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/vendor/profile` | Bearer (IsVendor) | — | — |
| PATCH | `/api/vendor/profile` | Bearer (IsVendor) | — | `name` (optional), `city` (optional), `bio` (optional), `price_from` (optional) |

### Feed & Comments
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/feed/posts` | Bearer | `page`=1, `limit`=20 | — |
| POST | `/api/feed/posts/{post_id}/like` | Bearer | — | — |
| DELETE | `/api/feed/posts/{post_id}/like` | Bearer | — | — |
| GET | `/api/feed/posts/{post_id}/comments` | Bearer | `page`=1, `limit`=20 | — |
| POST | `/api/feed/posts/{post_id}/comments` | Bearer | — | `text` (required), `parent_id` (optional) |
| POST | `/api/feed/comments/{comment_id}/like` | Bearer | — | — |

### Categories
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/categories` | None | `page`=1, `limit`=50 | — |
| GET | `/api/categories/{category_id}` | None | — | — |

### Favorites
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/users/me/favorites` | Bearer | `page`=1, `limit`=20 | — |
| POST | `/api/vendors/{vendor_id}/favorite` | Bearer | — | — |
| DELETE | `/api/vendors/{vendor_id}/favorite` | Bearer | — | — |

### Bookings
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/bookings` | Bearer | `page`=1, `limit`=20, `status` (optional) | — |
| POST | `/api/bookings` | Bearer | — | `vendor_id` (required), `event_type` (required), `booking_date` (required), `location` (optional), `amount` (optional), `deposit` (optional) |
| GET | `/api/bookings/{booking_id}` | Bearer | — | — |
| PATCH | `/api/bookings/{booking_id}` | Bearer | — | `status` (required; one of `pending`, `confirmed`, `completed`, `cancelled`) |

### Vendor Reviews (by vendor_id)
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/vendors/{vendor_id}/reviews` | None (AllowAny) | `page`=1, `limit`=20 | — |
| POST | `/api/vendors/{vendor_id}/reviews` | AllowAny (POST requires Bearer inside) | — | `booking_id` (required), `rating` (required), `comment` (optional) |

### Messaging / Conversations
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/conversations` | Bearer | `page`=1, `limit`=20 | — |
| POST | `/api/conversations` | Bearer | — | `partner_id` (required) |
| GET | `/api/conversations/{conversation_id}` | Bearer | — | — |
| DELETE | `/api/conversations/{conversation_id}` | Bearer | — | — |
| GET | `/api/conversations/{conversation_id}/messages` | Bearer | `page`=1, `limit`=20 | — |
| POST | `/api/conversations/{conversation_id}/messages` | Bearer | — | `text` (optional), `attachment_url` (optional) but at least one must be present |
| PATCH | `/api/conversations/{conversation_id}/read` | Bearer | — | — |

### Invitations
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/invitations/templates` | Bearer | `page`=1, `limit`=20, `type` (optional) | — |
| GET | `/api/invitations` | Bearer | `page`=1, `limit`=20 | — |
| POST | `/api/invitations` | Bearer | — | `invitation_type` (required), `event_type` (required), `answers` (optional; default `{}`), `template_id` (optional) |
| GET | `/api/invitations/{invitation_id}` | Bearer | — | — |
| DELETE | `/api/invitations/{invitation_id}` | Bearer | — | — |

### Vendor - Listings (self)
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/vendor/listings` | Bearer (IsVendor) | `page`=1, `limit`=20 | — |
| POST | `/api/vendor/listings` | Bearer (IsVendor) | — | `title` (required), `description` (optional), `price` (optional), `category` (optional) |
| PUT | `/api/vendor/listings/{listing_id}` | Bearer (IsVendor) | — | `title` (optional), `description` (optional), `price` (optional), `category` (optional) |
| DELETE | `/api/vendor/listings/{listing_id}` | Bearer (IsVendor) | — | — |

### Vendor - Posts (self)
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/vendor/posts` | Bearer (IsVendor) | `page`=1, `limit`=20 | — |
| POST | `/api/vendor/posts` | Bearer (IsVendor) | — | `caption` (optional; default `""`), `media` (optional; list of `{ url, is_video?, sort_order? }` where `url` is required per item) |
| DELETE | `/api/vendor/posts/{post_id}` | Bearer (IsVendor) | — | — |

### Vendor - Packages
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/vendors/{vendor_id}/packages` | None (AllowAny) | `page`=1, `limit`=20 | — |
| GET | `/api/vendor/packages` | Bearer (IsVendor) | `page`=1, `limit`=20 | — |
| POST | `/api/vendor/packages` | Bearer (IsVendor) | — | `name` (required), `price` (required), `features_text` (optional), `features_json` (optional), `is_active` (optional; default `true`) |
| PUT | `/api/vendor/packages/{package_id}` | Bearer (IsVendor) | — | `name` (optional), `price` (optional), `features_text` (optional), `features_json` (optional), `is_active` (optional) |
| DELETE | `/api/vendor/packages/{package_id}` | Bearer (IsVendor) | — | — |

### Vendor - Subscription
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/vendor/subscription` | Bearer (IsVendor) | — | — |
| GET | `/api/subscription/plans` | Bearer | `page`=1, `limit`=20 | — |

### Vendor - Analytics
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/vendor/analytics` | Bearer (IsVendor) | `from` (optional), `to` (optional) | — |

### Notifications
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/users/me/notifications` | Bearer | `page`=1, `limit`=20 | — |
| PATCH | `/api/users/me/notifications/{notification_id}/read` | Bearer | — | — |
| PATCH | `/api/users/me/notification-settings` | Bearer | — | `push` (optional), `email` (optional) |

### Admin
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| GET | `/api/admin/users` | Bearer (IsAdmin) | `role` (optional) | — |
| GET | `/api/admin/users/{user_id}` | Bearer (IsAdmin) | — | — |
| PATCH | `/api/admin/users/{user_id}/update` | Bearer (IsAdmin) | — | `role_name` (optional), `first_name` (optional), `last_name` (optional), `email` (optional), `phone` (optional), `is_active` (optional), `is_verified` (optional) |
| POST | `/api/admin/users/{user_id}/block` | Bearer (IsAdmin) | — | — |
| POST | `/api/admin/users/{user_id}/unblock` | Bearer (IsAdmin) | — | — |
| GET | `/api/admin/vendors` | Bearer (IsAdmin) | — | — |
| GET | `/api/admin/vendors/{vendor_id}` | Bearer (IsAdmin) | — | — |
| POST | `/api/admin/vendors/{vendor_id}/approve` | Bearer (IsAdmin) | — | — |
| POST | `/api/admin/vendors/{vendor_id}/reject` | Bearer (IsAdmin) | — | — |

### File Upload
| Method | Endpoint | Auth | Query Params | Body |
|---|---|---|---|---|
| POST | `/api/upload-file` | Bearer | — | multipart `file` (required), `path` (optional; folder/key prefix) |

