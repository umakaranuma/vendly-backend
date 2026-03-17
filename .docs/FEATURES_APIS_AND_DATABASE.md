# Vendly Mobile – Features, APIs & Database

This document describes the **Vendly Mobile** Flutter application: its features, recommended REST API endpoints, and database schema. The app currently uses **mock/demo data** and local storage (SharedPreferences) for auth; the APIs and tables below are specified so a backend can be built to support all flows.

---

## 1. Project Overview

**Vendly Mobile** is a celebration/events platform where:

- **Consumers (customers)** discover vendors (photographers, planners, makeup, decor, music), browse a feed, search, like vendors, manage bookings, send messages, and create invitations (text/video/website).
- **Vendors** manage listings, posts, bookings, and view analytics.
- **Admin** functionality is not implemented in the app; recommended admin endpoints and tables are included for backend management.

**Tech stack:** Flutter, GoRouter, GetIt, Dio (for future API), SharedPreferences (auth/session).

**Base URLs (from `lib/core/configs/env_config.dart`):**

| Mode   | Main API (`candidateBaseUrl`)                          | Identity (`idpBaseUrl`)                          |
|--------|--------------------------------------------------------|--------------------------------------------------|
| debug  | `https://dev-admin.joboro.apptimus.lk/api/candidates`  | `https://idp-ui.utilities.apptimus.lk/idp-api/api/` |
| demo   | `https://demo-api.empowerone.io/passenger/api/`        | (same)                                           |
| test   | `https://test-api.empowerone.io/passenger/api/`        | (same)                                           |
| uat    | `https://uat-api.empowerone.io/passenger/api/`         | (same)                                           |
| live   | `https://live-api.empowerone.io/passenger/api/`        | (same)                                           |

**Auth:** Bearer token in `Authorization` header. On 401, the client clears session (logout). Token and user/role are stored via `AuthDataSources` (SharedPreferences).

---

## 2. Feature List (by Flow)

| # | Feature | Side | Description |
|---|---------|------|-------------|
| 1 | Splash | All | Logo animation; navigates to `/home` after delay or tap. |
| 2 | Onboarding | All | Welcome screen; "Get started" → Register, "Login" → Login. |
| 3 | Register | All | Name, email, password, role (customer/vendor); then redirect to home. |
| 4 | Login | All | Email, password; role derived (e.g. vendor@gmail.com → vendor). Redirect to home. |
| 5 | Logout | All | Clear token/user/role; profile "Log out" or 401 handler. |
| 6 | Home shell | All | Bottom nav: Feed, Vendors, Likes, Bookings, Messages. Role-based Bookings tab. |
| 7 | Discover (Feed) | User | Feed of posts (images/video carousel), like/comment/share; comment → bottom sheet or login. |
| 8 | Global search | User | Search bar, recent searches, category chips; list vendors by query. |
| 9 | Vendors list | User | Category/price filters; vendor cards → vendor profile. |
| 10 | Vendor profile | User | Vendor name, gallery, Message / Book actions. |
| 11 | Favorites (Likes) | User | List of liked vendors. |
| 12 | Bookings (customer) | User | List/filter (All, Upcoming, Completed, Cancelled); booking cards. |
| 13 | Messages list | User | Conversation list with preview, time, unread. |
| 14 | Chat | User | Chat UI with a partner (vendor). |
| 15 | Profile | User | Cover/avatar, name; links to Edit, Liked vendors, Invitations, Notifications, Language, Theme, Help, Privacy, Log out. |
| 16 | Edit profile | User | Cover/avatar upload, display name, bio (and any extra fields). |
| 17 | Notifications settings | User | Toggle notification preferences. |
| 18 | Notifications inbox | User | List of notifications. |
| 19 | Language & region | User | App language/region selection. |
| 20 | Help & FAQ | User | Static help content. |
| 21 | Privacy & security | User | Privacy/security options. |
| 22 | Invitations list | User | List of created invitations; "Create invitation". |
| 23 | Create invitation | User | Type (text/video/website), event type, dynamic form (event-specific questions). |
| 24 | Choose invitation template | User | Pick template by type; preview card from filled details. |
| 25 | Vendor listings | Vendor | Manage service listings (vendor-only route). |
| 26 | Vendor posts | Vendor | List/create posts for feed (vendor-only). |
| 27 | Vendor create post | Vendor | Create a new feed post. |
| 28 | Vendor bookings | Vendor | List bookings with filters (Pending, Confirmed, Completed, Cancelled). |
| 29 | Vendor booking detail | Vendor | Single booking detail + calendar. |
| 30 | Vendor analytics | Vendor | Analytics dashboard. |
| 31 | Categories | User/Vendor/Admin | List categories (filter vendors); admin: full CRUD (create, read, update, delete). |
| 32 | Vendor reviews | User/Vendor | Give a review for a vendor **only if** that user/vendor has a **completed** booking with that vendor; one review per completed booking. |
| 33 | Admin: delete review | Admin | Admin can delete any vendor review (moderation). |

---

## 3. Application Flow (Register → Login → Features)

```
Splash (/) → Onboarding (/onboarding) → Register (/register) or Login (/login)
     → Home (/home)
         ├── Feed (Discover) → Search (/search) | Vendor profile (/vendors/profile)
         ├── Vendors → Vendor profile
         ├── Likes (/likes)
         ├── Bookings (/vendor/bookings for vendor, in-shell for customer)
         └── Messages → Chat (/chat)
Profile (/profile) → Edit (/profile/edit), Notifications, Language, Help, Privacy, Invitations (/invitations)
Invitations → Create (/invitations/create) → Choose template (/invitations/create/choose-template)
Vendor-only: /vendor/listings, /vendor/posts, /vendor/posts/create, /vendor/bookings, /vendor/booking/detail, /vendor/analytics
```

---

## 4. Per-Feature: APIs, Tables, and Relationships

### 4.1 Authentication (Register, Login, Logout)

**Current behaviour:** No API. Register/Login persist role, user, and token locally; logout clears them.

**Recommended REST API**

| Method | Path (IDP) | Request | Response |
|--------|------------|--------|----------|
| POST | `auth/register` | `{ "name", "email", "password", "role": "customer" \| "vendor" }` | `{ "is_success", "message", "result": { "user": User, "token": string }, "system_code"? }` |
| POST | `auth/login` | `{ "email", "password" }` | Same as above. |
| POST | `auth/logout` | (Bearer token) | 204 or 200. |
| POST | `auth/forgot-password` | `{ "email" }` | `{ "message" }` (for future "Forgot password?"). |

**User (from `lib/core/auth/model/login_response.dart`):**

- `id` (int), `name` (string), `email` (string, nullable).

**Recommended tables**

- **users**  
  - `id` PK, `name`, `email` UNIQUE NOT NULL, `password_hash`, `role` ('customer'|'vendor'|'admin'), `avatar_url`, `cover_url`, `bio`, `created_at`, `updated_at`.
- **sessions** (optional, for server-side session/token)  
  - `id` PK, `user_id` FK(users), `token`, `expires_at`, `created_at`.

**Relationships:** sessions → users (many-to-one).

---

### 4.2 Profile (View, Edit)

**Current behaviour:** Profile shows user from `AuthDataSources`; Edit profile allows cover/avatar pick (camera/gallery), display name, bio (no API).

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `users/me` | — | `User` (id, name, email, avatar_url, cover_url, bio, role, ...). |
| PUT | `users/me` | `{ "name", "avatar_url"? "cover_url"? "bio"? }` | Updated `User`. |
| POST | `upload-file` | multipart: `file`, `path` (key) | `{ "url" }` (e.g. S3/CDN URL for avatar/cover). |

**Recommended tables**

- **users** (see §4.1); add `avatar_url`, `cover_url`, `bio` if not already.

**Relationships:** None additional.

---

### 4.3 Discover (Feed) and Feed Comments

**Current behaviour:** Feed items and media are mock (e.g. `_DiscoverScreenMedia.feedMediaByIndex`). Comments open in a bottom sheet with mock `FeedCommentModel` (id, authorName, authorAvatarUrl, text, timeAgo, likeCount, isLiked, replies).

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `feed/posts` | `?page=1&limit=20` | `{ "items": [ FeedPost ], "next_page"? }` |
| GET | `feed/posts/:id/comments` | — | `{ "comments": [ FeedComment ], "total" }` |
| POST | `feed/posts/:id/comments` | `{ "text", "parent_id"? }` | `FeedComment`. |
| POST | `feed/posts/:id/like` | — | `{ "liked", "like_count" }` |
| DELETE | `feed/posts/:id/like` | — | 204. |
| POST | `feed/comments/:id/like` | — | 204. |

**Feed post (inferred):** id, vendor_id, media (list of { url, is_video }), caption, like_count, comment_count, created_at.  
**FeedComment (from `feed_comments_bottom_sheet.dart`):** id, author_name, author_avatar_url, text, time_ago, like_count, is_liked, replies (nested).

**Recommended tables**

- **posts**  
  - `id` PK, `vendor_id` FK(vendors), `caption`, `like_count`, `comment_count`, `created_at`, `updated_at`.
- **post_media**  
  - `id` PK, `post_id` FK(posts), `url`, `is_video`, `sort_order`.
- **post_likes**  
  - `id` PK, `post_id` FK(posts), `user_id` FK(users), `created_at`. UNIQUE(post_id, user_id).
- **comments**  
  - `id` PK, `post_id` FK(posts), `user_id` FK(users), `parent_id` FK(comments) NULL, `text`, `like_count`, `created_at`, `updated_at`.
- **comment_likes**  
  - `id` PK, `comment_id` FK(comments), `user_id` FK(users), `created_at`. UNIQUE(comment_id, user_id).

**Relationships:** posts → vendors; post_media → posts; post_likes → posts, users; comments → posts, users, parent comment; comment_likes → comments, users.

---

### 4.4 Global Search and Vendors List

**Current behaviour:** Search and vendors list use mock `_VendorSearchItem` (title, city, category, rating, reviews, priceFrom). Filter by category and price.

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `vendors` | `?q=&category_id=&category_slug=&min_price=&max_price=&page=1&limit=20` | `{ "items": [ Vendor ], "total" }` (returns **only approved vendors**: `status = 'approved'`). Filter by category via `category_id` or `category_slug`. |
| GET | `vendors/:id` | — | `Vendor` with gallery, services, etc. (only if vendor `status = 'approved'`; otherwise 404/403). |
| GET | `search/suggestions` | `?q=xxx` | `{ "recent"?: string[], "categories"?: Category[] }` (optional; categories from **categories** table). |

**Vendor (inferred):** id, title/name, city, category, rating, reviews count, price_from, gallery (urls), etc.

**Recommended tables**

- **vendors**  
  - `id` PK, `user_id` FK(users) UNIQUE (vendor account), `name`, `slug`, `city`, **`category_id`** FK(categories), `rating` (decimal), `review_count`, `price_from` (decimal or string for display), `bio`, **`status`** (`'pending' \| 'approved' \| 'rejected'`), **`approved_at`** (datetime, nullable), **`approved_by_admin_id`** FK(users, nullable), `created_at`, `updated_at`.
- **vendor_gallery**  
  - `id` PK, `vendor_id` FK(vendors), `url`, `sort_order`.
- **categories** (CRUD; see §4.4.1)  
  - `id` PK, `name`, `slug` UNIQUE, `description`, `sort_order`, `created_at`, `updated_at`.  
  - Vendors reference category via `category_id` FK(categories) in **vendors** table.

**Relationships:** vendors → users (one-to-one for vendor account); vendor_gallery → vendors; **vendors → categories** (many-to-one via `category_id`).

---

### 4.5 Favorites (Liked Vendors)

**Current behaviour:** Favorites screen shows mock "Liked vendors" list (e.g. Dream Weddings Studio, Aura Bridal, Golden Lens).

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `users/me/favorites` | — | `{ "items": [ Vendor ] }` |
| POST | `vendors/:id/favorite` | — | 201. |
| DELETE | `vendors/:id/favorite` | — | 204. |

**Recommended tables**

- **user_favorite_vendors**  
  - `id` PK, `user_id` FK(users), `vendor_id` FK(vendors), `created_at`. UNIQUE(user_id, vendor_id).

**Relationships:** user_favorite_vendors → users, vendors (many-to-many between users and vendors).

---

### 4.4.1 Categories (CRUD)

Categories are used to classify vendors (e.g. Photography, Makeup, Planning, Decor, Music). **Admin** can create, update, and delete categories; **users and vendors** can list and read them (e.g. for filters and display).

**Recommended REST API**

| Method | Path | Request | Response | Who |
|--------|------|--------|----------|-----|
| GET | `categories` | `?page=1&limit=50` | `{ "items": [ Category ], "total" }` | All (public or authenticated). |
| GET | `categories/:id` | — | `Category`. | All. |
| POST | `admin/categories` | `{ "name", "slug"? "description"? "sort_order"? }` | `Category`. | Admin. |
| PUT | `admin/categories/:id` | same | `Category`. | Admin. |
| DELETE | `admin/categories/:id` | — | 204. | Admin. |

**Category (inferred):** id, name, slug, description, sort_order, created_at, updated_at.

**Recommended tables**

- **categories**  
  - `id` PK, `name`, `slug` UNIQUE NOT NULL, `description` (text, nullable), `sort_order` (int, default 0), `created_at`, `updated_at`.

**Relationships:** vendors → categories (many-to-one: `vendors.category_id` FK(categories)); listings may also reference `category_id` if needed.

---

### 4.6 Bookings (Customer and Vendor)

**Current behaviour:** Customer Bookings screen: filter All/Upcoming/Completed/Cancelled; mock cards. Vendor Bookings: list with Pending/Confirmed/Completed/Cancelled; `VendorBookingDetailData`: customerName, eventType, bookingDate, location, amount, deposit, status.

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `bookings` | `?status=&page=1&limit=20` (customer: own; vendor: own vendor’s) | `{ "items": [ Booking ], "total" }` |
| GET | `bookings/:id` | — | `Booking` (full detail). |
| POST | `bookings` | `{ "vendor_id", "event_type", "booking_date", "location", "amount", "deposit", "message"? }` | `Booking`. |
| PATCH | `bookings/:id` | `{ "status": "confirmed" \| "cancelled" \| ... }` | `Booking`. |

**Booking (inferred):** id, customer_id, vendor_id, event_type, booking_date, location, amount, deposit, status (pending, confirmed, completed, cancelled), created_at, updated_at.

**Recommended tables**

- **bookings**  
  - `id` PK, `customer_id` FK(users), `vendor_id` FK(vendors), `event_type`, `booking_date` (date/datetime), `location`, `amount` (decimal or string), `deposit`, `status`, `created_at`, `updated_at`.

**Relationships:** bookings → users (customer), vendors (vendor).

---

### 4.6.1 Vendor Reviews (post completed booking)

**Business rule:** A **user** or **vendor** (as customer) can give a review for a vendor **only if** they have **booked** that vendor and the **booking status is completed**. One review per completed booking. **Admin** can delete any review (moderation).

**Recommended REST API**

| Method | Path | Request | Response | Who |
|--------|------|--------|----------|-----|
| GET | `vendors/:id/reviews` | `?page=1&limit=20` | `{ "items": [ Review ], "total", "average_rating" }` | All (for approved vendors). |
| POST | `vendors/:id/reviews` | `{ "booking_id", "rating", "comment"? }` | `Review`. | User or Vendor (booker); **allowed only if** `bookings.id = booking_id` has `customer_id = current_user` and `status = 'completed'`; one review per booking. |
| DELETE | `admin/reviews/:id` | — | 204. | Admin (delete review). |

**Review (inferred):** id, booking_id, reviewer_id (user_id), vendor_id, rating (1–5 or scale), comment (text), created_at. Optionally: reviewer display name, avatar (from users).

**Recommended tables**

- **vendor_reviews**  
  - `id` PK, **`booking_id`** FK(bookings) UNIQUE (one review per completed booking), **`reviewer_id`** FK(users), **`vendor_id`** FK(vendors), `rating` (decimal or int), `comment` (text, nullable), `created_at`, `updated_at`.  
  - **Constraint:** Backend must ensure the booking exists, `booking.status = 'completed'`, and `booking.customer_id = reviewer_id`, `booking.vendor_id = vendor_id`.

**Relationships:** vendor_reviews → bookings (one-to-one per booking), vendor_reviews → users (reviewer), vendor_reviews → vendors. Vendor’s `review_count` and `rating` can be derived/aggregated from `vendor_reviews`.

**Joins (example):**  
- List reviews for vendor: `vendor_reviews` JOIN `users` ON `vendor_reviews.reviewer_id = users.id` (for reviewer name/avatar).  
- Check if current user can review: `bookings` WHERE `customer_id = :user_id` AND `vendor_id = :vendor_id` AND `status = 'completed'` AND NOT EXISTS (SELECT 1 FROM vendor_reviews WHERE booking_id = bookings.id).

---

### 4.7 Messages and Chat

**Current behaviour:** Messages list: mock `_ConversationData` (name, preview, time, hasUnread, sentByMe). Chat screen: mock conversation by partner name.

**Recommended REST API (Chat Endpoints)**

| Method | Path | Query / Request | Response |
|--------|------|-----------------|----------|
| GET | `conversations` | — | `{ "items": [ Conversation ], "total": number }` |
| GET | `conversations/:id` | — | `Conversation` (full detail + participants). |
| GET | `conversations/:id/messages` | `?before=<message_id>&limit=20` (cursor pagination) | `{ "items": [ Message ], "has_more": boolean, "next_cursor"?: string }` |
| POST | `conversations` | Body: `{ "partner_id": number }` or `{ "vendor_id": number }` | `Conversation`; 201. If conversation exists for same pair, return 200 + existing. |
| POST | `conversations/:id/messages` | Body: `{ "text": string }` or multipart: `file` (attachment) | `Message` (id, conversation_id, sender_id, text, attachment_url?, created_at, read_at?). |
| PATCH | `conversations/:id/read` | — | 204. Marks all messages as read for current user. |
| DELETE | `conversations/:id` | — | 204. Leave/archive (optional; soft-delete for participant). |

**Request / Response shapes**

- **GET conversations – Response item (Conversation list item)**  
  `id`, `participants`: [ `{ "user_id", "name", "avatar_url", "role" }` ], `last_message`: `{ "id", "text", "sender_id", "created_at", "sent_by_me": boolean }`, `unread_count`: number, `updated_at`.

- **GET conversations/:id – Response (Conversation detail)**  
  `id`, `participants`: [ `{ "user_id", "name", "avatar_url", "role" }` ], `created_at`, `updated_at`, optional `last_message`.

- **GET conversations/:id/messages – Response item (Message)**  
  `id`, `conversation_id`, `sender_id`, `text`, `attachment_url` (nullable), `created_at`, `read_at` (nullable). Optional: `sender`: `{ "id", "name", "avatar_url" }`.

- **POST conversations – Request**  
  - `partner_id` (user id) – to chat with another user (e.g. vendor’s user_id).  
  - Or `vendor_id` – to start chat with a vendor (backend resolves to vendor’s user_id).  
  Response: full `Conversation`. If conversation already exists for this pair, return it (idempotent).

- **POST conversations/:id/messages – Request**  
  - `text`: string (required, or send attachment).  
  - Optional: multipart with `file` → backend returns `Message` with `attachment_url` (e.g. S3/CDN).

**Recommended tables**

- **conversations**  
  - `id` PK, `created_at`, `updated_at`.  
  - Optional: for two-party only, add `user1_id`, `user2_id` FK(users) with UNIQUE(user1_id, user2_id) to find existing chat.

- **conversation_participants**  
  - `id` PK, `conversation_id` FK(conversations), `user_id` FK(users), `last_read_at` (datetime, nullable), `joined_at`, `left_at` (nullable). UNIQUE(conversation_id, user_id).

- **messages**  
  - `id` PK, `conversation_id` FK(conversations), `sender_id` FK(users), `text` (text), `attachment_url` (nullable), `created_at`, `updated_at`.  
  - Optional: **message_read_receipts** – `id` PK, `message_id` FK(messages), `user_id` FK(users), `read_at`. UNIQUE(message_id, user_id).

**Relationships**

- conversations ↔ users (many-to-many via conversation_participants).
- messages → conversations (many-to-one), messages → users (sender).
- conversation_participants → conversations, users.

**Joins (examples)**

- **List conversations for current user:**  
  `conversation_participants` WHERE `user_id = :current_user_id`  
  JOIN `conversations` ON conversation_id = conversations.id  
  JOIN other participants (users) for partner name/avatar;  
  subquery or join for last message: latest row in `messages` for that conversation.

- **List messages (chat):**  
  `messages` WHERE `conversation_id = :id` ORDER BY `created_at` DESC; paginate with `before = message_id` and LIMIT.

- **Unread count:**  
  For current user’s participant row, compare `last_read_at` with max(messages.created_at) for conversation; or use message_read_receipts.

---

### 4.8 Invitations

**Current behaviour:** Create invitation: type (text/video/website), event type (wedding, pubertyCeremony, householdFunction, birthday, engagement, other), dynamic form from `getInvitationQuestions`; submit → `FilledInvitationDetails` (invitationType, eventType, answers map). Then choose template (`InvitationTemplate`: id, name, description, style, icon). Templates are per type (e.g. card_floral, video_standard, website_standard). Invitation config uses keys like groom_name, bride_name, event_date, event_time, venue_name, venue_address, dress_code, personal_message, etc.

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `invitations` | `?page=1&limit=20` | `{ "items": [ Invitation ], "total" }` |
| POST | `invitations` | `{ "invitation_type": "card" \| "video" \| "website", "event_type": "wedding" \| ... , "answers": { key: value }, "template_id"? }` | `Invitation`. |
| GET | `invitations/:id` | — | `Invitation` (full detail + template). |
| GET | `invitations/templates` | `?type=card \| video \| website` | `{ "items": [ InvitationTemplate ] }` |
| DELETE | `invitations/:id` | — | 204. |

**Invitation (inferred):** id, user_id, invitation_type, event_type, template_id, answers (JSON or normalized fields), created_at, updated_at.  
**InvitationTemplate:** id, name, description, style, icon (or asset path), type.

**Recommended tables**

- **invitations**  
  - `id` PK, `user_id` FK(users), `invitation_type` ('card'|'video'|'website'), `event_type`, `template_id` FK(invitation_templates), `answers` (JSONB or similar), `created_at`, `updated_at`.
- **invitation_templates**  
  - `id` PK, `name`, `description`, `style`, `icon`, `invitation_type`, `sort_order`.

**Relationships:** invitations → users; invitations → invitation_templates.

---

### 4.9 Vendor Listings, Posts, Create Post

**Current behaviour:** Vendor-only screens: list listings, list posts, create post. All mock.

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `vendors/me/listings` | — | `{ "items": [ Listing ] }` |
| POST | `vendors/me/listings` | `{ "title", "description", "price", "category", ... }` | `Listing`. |
| PUT | `vendors/me/listings/:id` | same | `Listing`. |
| DELETE | `vendors/me/listings/:id` | — | 204. |
| GET | `vendors/me/posts` | — | `{ "items": [ Post ] }` (same as feed posts). |
| POST | `vendors/me/posts` | multipart or `{ "caption", "media": [ { "url", "is_video" } ] }` | `Post`. |
| DELETE | `vendors/me/posts/:id` | — | 204. |

**Recommended tables**

- **listings** (generic vendor services/offerings)  
  - `id` PK, `vendor_id` FK(vendors), `title`, `description`, `price`, `category`, `created_at`, `updated_at`.
- **posts** (already in §4.3); **post_media** (already in §4.3).

**Relationships:** listings → vendors; posts → vendors (already defined).

---

### 4.9.1 Vendor Packages & Subscription Limits

Vendors can define **their own packages** on top of generic listings. For example, a photographer can create:

- `Medium`, `8000`, features: *3 hours with 1 camera*  
- `Premium`, `12000`, features: *5 hours with 2 cameras + album*  

The **system (admin)** controls how many custom packages a vendor can create based on the vendor’s **subscription plan** (e.g. *free* vendors can create only **2** packages).

#### 4.9.1.1 Business rules

- Every vendor can create multiple **vendor_packages** under their profile.
- Each package has: **name**, **amount/price**, **features** (list or text).
- The number of active packages per vendor is limited by their **subscription plan** (`subscription_plans.max_packages`).
- Default: vendors without a paid plan are on a **free** plan with a small limit (e.g. `max_packages = 2`).
- Admin can create and manage system-level subscription plans and assign them to vendors.

#### 4.9.1.2 Recommended REST API

**Vendor packages (per vendor)**

| Method | Path | Request | Response | Who |
|--------|------|--------|----------|-----|
| GET | `vendors/:vendor_id/packages` | — | `{ "items": [ VendorPackage ] }` | All (public; only for approved vendors). |
| GET | `vendors/me/packages` | — | `{ "items": [ VendorPackage ] }` | Vendor (own packages). |
| POST | `vendors/me/packages` | `{ "name", "price", "features": string[] \| string, \"is_active\"? }` | `VendorPackage`. | Vendor (subject to `max_packages` limit). |
| PUT | `vendors/me/packages/:id` | same as POST | `VendorPackage`. | Vendor (can edit their own package). |
| DELETE | `vendors/me/packages/:id` | — | 204. | Vendor (soft delete or hard delete, up to backend). |

**Subscription plans (system-level)**

| Method | Path | Request | Response | Who |
|--------|------|--------|----------|-----|
| GET | `subscription/plans` | — | `{ "items": [ SubscriptionPlan ] }` | Vendors/Admin (read). |
| POST | `admin/subscription/plans` | `{ "name", "max_packages", "price"?, \"description\"? }` | `SubscriptionPlan`. | Admin. |
| PUT | `admin/subscription/plans/:id` | same | `SubscriptionPlan`. | Admin. |
| DELETE | `admin/subscription/plans/:id` | — | 204. | Admin. |

**Vendor subscription assignment**

| Method | Path | Request | Response | Who |
|--------|------|--------|----------|-----|
| GET | `vendors/me/subscription` | — | `VendorSubscription` (current plan, limits, expiry). | Vendor. |
| GET | `admin/vendors/:id/subscription` | — | `VendorSubscription`. | Admin. |
| POST | `admin/vendors/:id/subscription` | `{ \"plan_id\", \"starts_at\"?, \"ends_at\"? }` | `VendorSubscription`. | Admin (assign/upgrade/downgrade). |

> The backend enforces the **package count limit**: before creating a new `vendor_package`, it checks the vendor’s active subscription (from `vendor_subscriptions` and `subscription_plans.max_packages`).

#### 4.9.1.3 Models

- **VendorPackage (inferred):**  
  `id`, `vendor_id`, `name`, `price`, `features` (string[] or text), `is_active`, `created_at`, `updated_at`.

- **SubscriptionPlan (inferred):**  
  `id`, `name` (e.g. Free, Standard, Premium), `max_packages` (int), `price` (optional, if you charge vendors), `description`, `created_at`, `updated_at`.

- **VendorSubscription (inferred):**  
  `id`, `vendor_id`, `plan_id`, `starts_at`, `ends_at` (nullable for ongoing), `is_active`, `created_at`, `updated_at`.

#### 4.9.1.4 Recommended tables

- **vendor_packages**  
  - `id` PK, `vendor_id` FK(vendors), `name` (e.g. Medium, Premium), `price` (decimal or int), `features_text` (text, nullable) **or** `features_json` (JSON array), `is_active` (bool, default true), `created_at`, `updated_at`.

- **subscription_plans**  
  - `id` PK, `name` (e.g. Free, Silver, Gold), `max_packages` (int, NOT NULL), `price` (decimal, nullable), `description` (text, nullable), `created_at`, `updated_at`.

- **vendor_subscriptions**  
  - `id` PK, `vendor_id` FK(vendors), `plan_id` FK(subscription_plans), `starts_at`, `ends_at` (nullable), `is_active` (bool), `created_at`, `updated_at`.  
  - (Optional) UNIQUE(`vendor_id`, `is_active` WHERE `is_active = true`) so a vendor has at most one active subscription.

**Relationships:**

- vendor_packages → vendors (many packages per vendor).
- vendor_subscriptions → vendors; vendor_subscriptions → subscription_plans.
- vendors → subscription_plans via active row in vendor_subscriptions (one active plan per vendor).

---

### 4.10 Vendor Analytics

**Current behaviour:** Vendor analytics screen; mock data.

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `vendors/me/analytics` | `?from=&to=` | `{ "views", "likes", "bookings_count", "revenue", "chart_data"? }` |

**Recommended tables**

- Use existing **bookings**, **post_likes**, **user_favorite_vendors**; optionally **vendor_views** (id, vendor_id, user_id?, viewed_at) for view counts.

**Relationships:** Aggregations over existing tables.

---

### 4.11 Notifications

**Current behaviour:** Notifications settings and inbox screens; placeholders.

**Recommended REST API**

| Method | Path | Request | Response |
|--------|------|--------|----------|
| GET | `users/me/notifications` | `?page=1&limit=20` | `{ "items": [ Notification ], "unread_count" }` |
| PATCH | `users/me/notifications/:id/read` | — | 204. |
| PATCH | `users/me/notification-settings` | `{ "push", "email", ... }` | 200. |

**Recommended tables**

- **notifications**  
  - `id` PK, `user_id` FK(users), `type`, `title`, `body`, `data` (JSON), `read_at`, `created_at`.
- **user_notification_settings**  
  - `id` PK, `user_id` FK(users) UNIQUE, `push_enabled`, `email_enabled`, etc., `updated_at`.

**Relationships:** notifications → users.

---

## 5. Admin – Recommended Endpoints and Tables

The app has **no admin UI**; the following support backend administration.

**Recommended REST API (admin)**

| Method | Path | Description |
|--------|------|-------------|
| GET | `admin/users` | List users (paginated, filter by role). |
| GET | `admin/users/:id` | User detail. |
| PATCH | `admin/users/:id` | Update user (e.g. role, suspend). |
| GET | `admin/vendors` | List vendors; filter by `status` (`pending`, `approved`, `rejected`). |
| PATCH | `admin/vendors/:id/approve` | Approve vendor → sets `status = 'approved'`, `approved_at`, `approved_by_admin_id`. |
| PATCH | `admin/vendors/:id/reject` | Reject/suspend vendor → sets `status = 'rejected'` or `status = 'suspended'`. |
| GET | `admin/posts` | List all posts; filter by vendor. |
| DELETE | `admin/posts/:id` | Remove post (moderation). |
| GET | `admin/bookings` | List all bookings. |
| GET | `admin/conversations` | List all conversations (paginated; filter by user_id optional). |
| GET | `admin/conversations/:id/messages` | List messages in a conversation (moderation/support). |
| DELETE | `admin/messages/:id` | Delete a message (moderation). |
| GET | `admin/invitations` | List all invitations. |
| GET | `admin/notifications` | Send or list system notifications. |
| GET | `admin/categories` | List all categories (same as public; admin may need for dropdowns). |
| POST | `admin/categories` | Create category. |
| PUT | `admin/categories/:id` | Update category. |
| DELETE | `admin/categories/:id` | Delete category. |
| DELETE | `admin/reviews/:id` | Delete a vendor review (moderation). |

**Recommended tables**

- **users** already has `role` ('admin').
- Optional: **audit_log** (id, actor_id, action, resource_type, resource_id, payload, created_at) for admin actions.
- Content moderation: use existing **posts**, **comments**; add `moderation_status` or `hidden_at` if needed.

**Relationships:** Same as above; admin acts on users, vendors, posts, bookings, invitations.

---

## 6. Summary of All Tables and Relationships

### 6.1 Table Summary

| Table | Primary key | Main fields |
|-------|-------------|-------------|
| users | id | name, email, password_hash, role, avatar_url, cover_url, bio, created_at, updated_at |
| sessions | id | user_id (FK), token, expires_at, created_at |
| categories | id | name, slug UNIQUE, description, sort_order, created_at, updated_at |
| vendors | id | user_id (FK), name, slug, city, **category_id (FK categories)**, rating, review_count, price_from, bio, **status**, **approved_at**, **approved_by_admin_id (FK users)**, created_at, updated_at |
| vendor_gallery | id | vendor_id (FK), url, sort_order |
| posts | id | vendor_id (FK), caption, like_count, comment_count, created_at, updated_at |
| post_media | id | post_id (FK), url, is_video, sort_order |
| post_likes | id | post_id (FK), user_id (FK), created_at |
| comments | id | post_id (FK), user_id (FK), parent_id (FK), text, like_count, created_at, updated_at |
| comment_likes | id | comment_id (FK), user_id (FK), created_at |
| user_favorite_vendors | id | user_id (FK), vendor_id (FK), created_at |
| bookings | id | customer_id (FK), vendor_id (FK), event_type, booking_date, location, amount, deposit, status, created_at, updated_at |
| vendor_reviews | id | **booking_id (FK) UNIQUE**, **reviewer_id (FK users)**, **vendor_id (FK)**, rating, comment, created_at, updated_at |
| conversations | id | created_at, updated_at |
| conversation_participants | id | conversation_id (FK), user_id (FK), last_read_at, joined_at, left_at |
| messages | id | conversation_id (FK), sender_id (FK), text, attachment_url, created_at, updated_at |
| message_read_receipts (optional) | id | message_id (FK), user_id (FK), read_at. UNIQUE(message_id, user_id) |
| invitations | id | user_id (FK), invitation_type, event_type, template_id (FK), answers (JSON), created_at, updated_at |
| invitation_templates | id | name, description, style, icon, invitation_type, sort_order |
| listings | id | vendor_id (FK), title, description, price, category, created_at, updated_at |
| vendor_packages | id | vendor_id (FK), name, price, features_text or features_json, is_active, created_at, updated_at |
| subscription_plans | id | name, max_packages, price, description, created_at, updated_at |
| vendor_subscriptions | id | vendor_id (FK), plan_id (FK), starts_at, ends_at, is_active, created_at, updated_at |
| notifications | id | user_id (FK), type, title, body, data (JSON), read_at, created_at |
| user_notification_settings | id | user_id (FK), push_enabled, email_enabled, updated_at |

### 6.2 Entity Relationship Overview

- **users** – central: sessions, vendors (1:1 for vendor account), post_likes, comment_likes, comments, user_favorite_vendors, bookings (as customer), **vendor_reviews (as reviewer)**, conversation_participants, messages (as sender), invitations, notifications, user_notification_settings.
- **categories** – CRUD by admin; referenced by vendors (and optionally listings).
- **vendors** – from users (1:1); reference categories; have posts, vendor_gallery, listings, **vendor_packages**, bookings (as vendor), **vendor_reviews**; link to **subscription_plans** via active **vendor_subscriptions**.
- **posts** – belong to vendors; have post_media, post_likes, comments.
- **comments** – belong to posts and optionally parent comment; have comment_likes.
- **bookings** – link users (customer) and vendors; **one vendor_review per completed booking**.
- **vendor_reviews** – one per completed booking; reviewer (user) and vendor; admin can delete.
- **conversations** – link users via conversation_participants; have messages.
- **invitations** – belong to users; reference invitation_templates.
- **subscription_plans** – define system-level limits (e.g. `max_packages`) per vendor tier; admin-managed.
- **vendor_subscriptions** – link vendors to subscription_plans and enforce limits like number of vendor_packages.

---

## 7. Notes on Current App State

- **No live API calls** are made today; `ApiBaseRequests` and base URLs are set up for when the backend is ready.
- **Auth:** Register/Login only write to SharedPreferences; no `AuthRepository` or IDP/candidate API calls.
- **File upload:** `file_upload_datasourses.dart` is commented out; it would POST to `upload-file` with multipart form data.
- **Repositories:** `AuthRepository` and `JobDataSource` are commented out in `service_locator.dart`.
- This document defines the **target** API and schema so the backend and future app integration can align with the existing UI and models.

---

*Generated from the Vendly Mobile codebase. Update this doc when adding new features or endpoints.*
