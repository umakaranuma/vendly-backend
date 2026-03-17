# Vendly Mobile – Database Schema Reference

> Complete schema for all recommended tables. Designed to support the Vendly Mobile Flutter application backend.

---

## Table of Contents

1. [users](#1-users)
2. [sessions](#2-sessions)
3. [categories](#3-categories)
4. [vendors](#4-vendors)
5. [vendor_gallery](#5-vendor_gallery)
6. [posts](#6-posts)
7. [post_media](#7-post_media)
8. [post_likes](#8-post_likes)
9. [comments](#9-comments)
10. [comment_likes](#10-comment_likes)
11. [user_favorite_vendors](#11-user_favorite_vendors)
12. [bookings](#12-bookings)
13. [vendor_reviews](#13-vendor_reviews)
14. [conversations](#14-conversations)
15. [conversation_participants](#15-conversation_participants)
16. [messages](#16-messages)
17. [message_read_receipts](#17-message_read_receipts-optional)
18. [invitations](#18-invitations)
19. [invitation_templates](#19-invitation_templates)
20. [listings](#20-listings)
21. [vendor_packages](#21-vendor_packages)
22. [subscription_plans](#22-subscription_plans)
23. [vendor_subscriptions](#23-vendor_subscriptions)
24. [notifications](#24-notifications)
25. [user_notification_settings](#25-user_notification_settings)
26. [vendor_views (optional)](#26-vendor_views-optional)
27. [audit_log (optional)](#27-audit_log-optional)

---

## 1. users

Central user table for all roles (customer, vendor, admin).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT / BIGINT | PK, AUTO INCREMENT | |
| name | VARCHAR(255) | NOT NULL | Display name |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login identifier |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt or similar |
| role | ENUM | NOT NULL | `'customer' \| 'vendor' \| 'admin'` |
| avatar_url | TEXT | NULL | Profile photo URL |
| cover_url | TEXT | NULL | Cover photo URL |
| bio | TEXT | NULL | Short bio |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 2. sessions

Optional server-side token management.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| user_id | INT | FK → users.id, NOT NULL | |
| token | TEXT | NOT NULL | Bearer token |
| expires_at | TIMESTAMP | NOT NULL | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Relationships:** Many sessions per user.

---

## 3. categories

Vendor categories (e.g. Photography, Makeup, Planning, Décor, Music). Admin-managed.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| name | VARCHAR(255) | NOT NULL | Display name |
| slug | VARCHAR(255) | UNIQUE, NOT NULL | URL-safe identifier |
| description | TEXT | NULL | |
| sort_order | INT | DEFAULT 0 | Display ordering |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 4. vendors

Vendor profile linked one-to-one with a user account.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| user_id | INT | FK → users.id, UNIQUE, NOT NULL | One vendor per user |
| name | VARCHAR(255) | NOT NULL | Business name |
| slug | VARCHAR(255) | UNIQUE | URL-safe identifier |
| city | VARCHAR(255) | NULL | |
| category_id | INT | FK → categories.id, NULL | Primary category |
| rating | DECIMAL(3,2) | DEFAULT 0.00 | Aggregated from vendor_reviews |
| review_count | INT | DEFAULT 0 | Aggregated |
| price_from | DECIMAL(10,2) | NULL | Starting price |
| bio | TEXT | NULL | |
| status | ENUM | NOT NULL, DEFAULT 'pending' | `'pending' \| 'approved' \| 'rejected' \| 'suspended'` |
| approved_at | TIMESTAMP | NULL | |
| approved_by_admin_id | INT | FK → users.id, NULL | Admin who approved |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Note:** Only vendors with `status = 'approved'` are returned in public search results.

---

## 5. vendor_gallery

Media gallery images for a vendor's profile.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| url | TEXT | NOT NULL | Image/video URL |
| sort_order | INT | DEFAULT 0 | |

---

## 6. posts

Feed posts created by vendors.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| caption | TEXT | NULL | |
| like_count | INT | DEFAULT 0 | Denormalized counter |
| comment_count | INT | DEFAULT 0 | Denormalized counter |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 7. post_media

Media files attached to a post (images or videos).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| post_id | INT | FK → posts.id, NOT NULL | |
| url | TEXT | NOT NULL | |
| is_video | BOOLEAN | DEFAULT FALSE | |
| sort_order | INT | DEFAULT 0 | |

---

## 8. post_likes

Tracks which users liked which posts.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| post_id | INT | FK → posts.id, NOT NULL | |
| user_id | INT | FK → users.id, NOT NULL | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint:** UNIQUE(post_id, user_id)

---

## 9. comments

User comments on feed posts. Supports nested replies via `parent_id`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| post_id | INT | FK → posts.id, NOT NULL | |
| user_id | INT | FK → users.id, NOT NULL | |
| parent_id | INT | FK → comments.id, NULL | NULL = top-level comment |
| text | TEXT | NOT NULL | |
| like_count | INT | DEFAULT 0 | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 10. comment_likes

Tracks which users liked which comments.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| comment_id | INT | FK → comments.id, NOT NULL | |
| user_id | INT | FK → users.id, NOT NULL | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint:** UNIQUE(comment_id, user_id)

---

## 11. user_favorite_vendors

Many-to-many: users favoriting vendors.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| user_id | INT | FK → users.id, NOT NULL | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint:** UNIQUE(user_id, vendor_id)

---

## 12. bookings

Service bookings between customers and vendors.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| customer_id | INT | FK → users.id, NOT NULL | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| event_type | VARCHAR(255) | NOT NULL | e.g. Wedding, Birthday |
| booking_date | DATETIME | NOT NULL | |
| location | VARCHAR(255) | NULL | |
| amount | DECIMAL(10,2) | NULL | Total amount |
| deposit | DECIMAL(10,2) | NULL | |
| status | ENUM | NOT NULL, DEFAULT 'pending' | `'pending' \| 'confirmed' \| 'completed' \| 'cancelled'` |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 13. vendor_reviews

Customer reviews for vendors, tied strictly to a completed booking.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| booking_id | INT | FK → bookings.id, UNIQUE, NOT NULL | One review per booking |
| reviewer_id | INT | FK → users.id, NOT NULL | Must match booking.customer_id |
| vendor_id | INT | FK → vendors.id, NOT NULL | Must match booking.vendor_id |
| rating | DECIMAL(3,2) | NOT NULL | e.g. 1.0–5.0 |
| comment | TEXT | NULL | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Business constraint:** Backend must verify `bookings.status = 'completed'` and `bookings.customer_id = reviewer_id` before inserting. Admin can delete any review.

---

## 14. conversations

A conversation thread between two or more participants.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Optional:** Add `user1_id` and `user2_id` with UNIQUE(user1_id, user2_id) for fast two-party lookups.

---

## 15. conversation_participants

Junction table linking users to conversations.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| conversation_id | INT | FK → conversations.id, NOT NULL | |
| user_id | INT | FK → users.id, NOT NULL | |
| last_read_at | TIMESTAMP | NULL | For unread count calculation |
| joined_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| left_at | TIMESTAMP | NULL | NULL = still active |

**Constraint:** UNIQUE(conversation_id, user_id)

---

## 16. messages

Individual messages within a conversation.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| conversation_id | INT | FK → conversations.id, NOT NULL | |
| sender_id | INT | FK → users.id, NOT NULL | |
| text | TEXT | NULL | At least one of text or attachment_url required |
| attachment_url | TEXT | NULL | CDN/S3 URL |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 17. message_read_receipts (Optional)

Per-message read receipts for fine-grained tracking.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| message_id | INT | FK → messages.id, NOT NULL | |
| user_id | INT | FK → users.id, NOT NULL | |
| read_at | TIMESTAMP | NOT NULL | |

**Constraint:** UNIQUE(message_id, user_id)

---

## 18. invitations

User-created event invitations (text/video/website).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| user_id | INT | FK → users.id, NOT NULL | |
| invitation_type | ENUM | NOT NULL | `'card' \| 'video' \| 'website'` |
| event_type | VARCHAR(255) | NOT NULL | e.g. wedding, birthday, engagement |
| template_id | INT | FK → invitation_templates.id, NULL | |
| answers | JSONB / JSON | NULL | Event-specific field answers |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Example answers keys:** `groom_name`, `bride_name`, `event_date`, `event_time`, `venue_name`, `venue_address`, `dress_code`, `personal_message`

---

## 19. invitation_templates

Predefined invitation templates per type.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| name | VARCHAR(255) | NOT NULL | e.g. card_floral, video_standard |
| description | TEXT | NULL | |
| style | VARCHAR(255) | NULL | e.g. floral, modern |
| icon | TEXT | NULL | Asset path or URL |
| invitation_type | ENUM | NOT NULL | `'card' \| 'video' \| 'website'` |
| sort_order | INT | DEFAULT 0 | |

---

## 20. listings

Generic vendor service offerings.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| title | VARCHAR(255) | NOT NULL | |
| description | TEXT | NULL | |
| price | DECIMAL(10,2) | NULL | |
| category | VARCHAR(255) | NULL | Free-text or FK to categories |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 21. vendor_packages

Custom service packages defined by vendors. Count is limited by subscription plan.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | e.g. Medium, Premium |
| price | DECIMAL(10,2) | NOT NULL | |
| features_text | TEXT | NULL | Plain-text feature list |
| features_json | JSON | NULL | Structured feature array |
| is_active | BOOLEAN | DEFAULT TRUE | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Business rule:** Before inserting, backend checks `vendor_subscriptions` → `subscription_plans.max_packages` for the vendor.

---

## 22. subscription_plans

System-level subscription tiers defining vendor limits.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| name | VARCHAR(255) | NOT NULL | e.g. Free, Silver, Gold |
| max_packages | INT | NOT NULL | Max vendor_packages allowed |
| price | DECIMAL(10,2) | NULL | Monthly/yearly charge (if applicable) |
| description | TEXT | NULL | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 23. vendor_subscriptions

Links vendors to their active subscription plan.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| plan_id | INT | FK → subscription_plans.id, NOT NULL | |
| starts_at | TIMESTAMP | NOT NULL | |
| ends_at | TIMESTAMP | NULL | NULL = indefinite |
| is_active | BOOLEAN | DEFAULT TRUE | |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Optional constraint:** UNIQUE(vendor_id) WHERE is_active = TRUE — ensures one active subscription per vendor.

---

## 24. notifications

In-app notifications for users.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| user_id | INT | FK → users.id, NOT NULL | |
| type | VARCHAR(255) | NOT NULL | e.g. booking_confirmed, new_message |
| title | VARCHAR(255) | NOT NULL | |
| body | TEXT | NULL | |
| data | JSON | NULL | Extra metadata |
| read_at | TIMESTAMP | NULL | NULL = unread |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 25. user_notification_settings

Per-user notification preferences.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| user_id | INT | FK → users.id, UNIQUE, NOT NULL | |
| push_enabled | BOOLEAN | DEFAULT TRUE | |
| email_enabled | BOOLEAN | DEFAULT TRUE | |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 26. vendor_views (Optional)

Tracks profile view events for vendor analytics.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| vendor_id | INT | FK → vendors.id, NOT NULL | |
| user_id | INT | FK → users.id, NULL | NULL = anonymous view |
| viewed_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## 27. audit_log (Optional)

Tracks admin actions for accountability.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INT | PK, AUTO INCREMENT | |
| actor_id | INT | FK → users.id, NOT NULL | Admin user who performed the action |
| action | VARCHAR(255) | NOT NULL | e.g. approve_vendor, delete_review |
| resource_type | VARCHAR(255) | NULL | e.g. vendor, post, review |
| resource_id | INT | NULL | ID of affected record |
| payload | JSON | NULL | Before/after state or extra context |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

---

## Entity Relationship Overview

```
users (central)
  ├── sessions (many)
  ├── vendors (1:1 for vendor account)
  │     ├── vendor_gallery
  │     ├── posts → post_media, post_likes, comments → comment_likes
  │     ├── listings
  │     ├── vendor_packages
  │     ├── vendor_subscriptions → subscription_plans
  │     └── vendor_reviews (received)
  ├── bookings (as customer)
  ├── vendor_reviews (as reviewer)
  ├── user_favorite_vendors → vendors
  ├── conversation_participants → conversations → messages
  ├── invitations → invitation_templates
  ├── notifications
  └── user_notification_settings

categories
  └── vendors (many vendors per category)
```

---

*Schema generated from `FEATURES_APIS_AND_DATABASE.md`. Validate all constraints and data types against your chosen database engine (PostgreSQL recommended for JSONB support).*
