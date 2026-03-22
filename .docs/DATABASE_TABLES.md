# Database tables and columns (vendly_backend)

This document lists **physical table names** (`db_table`) and **columns** as defined by Django models under `vendly_backend/models/`. Foreign keys are stored as `*_id` unless `db_column` overrides the name.

---

## Core / auth

| Table | Columns |
|--------|---------|
| **`core_roles`** | `id`, `name`, `description`, `created_at`, `updated_at` |
| **`core_statuses`** | `id`, `entity_type`, `name`, `status_type`, `sort_order`, `created_at`, `updated_at` |
| **`core_users`** | `id`, `password`, `last_login` (Django auth base), `email`, `phone`, `first_name`, `last_name`, `avatar_url`, `cover_url`, `bio`, `is_active`, `is_staff`, `is_superuser`, `is_verified`, `status_id` → `core_statuses`, `role_id` → `core_roles`, `created_at`, `updated_at` |
| **`core_vendor_profiles`** | `id`, `user_id` → `core_users`, `store_name`, `business_name`, `address`, `city`, `state`, `country`, `postal_code`, `latitude`, `longitude`, `contact_email`, `contact_phone`, `is_approved`, `is_blocked`, `rejection_reason`, `created_at`, `updated_at` |

Django also creates M2M tables for `CoreUser` permissions: **`core_users_groups`**, **`core_users_user_permissions`** (from `PermissionsMixin`).

---

## Users / notifications

| Table | Columns |
|--------|---------|
| **`sessions`** | `id`, `user_id` → `core_users`, `token`, `expires_at`, `created_at` |
| **`notifications`** | `id`, `user_id` → `core_users`, `type`, `title`, `body`, `data`, `read_at`, `created_at` |
| **`user_notification_settings`** | `id`, `user_id` → `core_users`, `push_enabled`, `email_enabled`, `updated_at` |

---

## Vendors / catalog / commerce

| Table | Columns |
|--------|---------|
| **`categories`** | `id`, `name`, `slug`, `description`, `sort_order`, `created_at`, `updated_at` |
| **`vendors`** | `id`, `user_id` → `core_users`, `name`, `slug`, `city`, `category_id` → `categories`, `rating`, `review_count`, `price_from`, `bio`, `status`, `status_id` → `core_statuses`, `approved_at`, `approved_by_admin_id` → `core_users`, `created_at`, `updated_at` |
| **`vendor_gallery`** | `id`, `vendor_id` → `vendors`, `url`, `sort_order` |
| **`listings`** | `id`, `vendor_id` → `vendors`, `title`, `description`, `price`, `category` (text), `created_at`, `updated_at` |
| **`subscription_plans`** | `id`, `name`, `max_packages`, `price`, `description`, `created_at`, `updated_at` |
| **`vendor_packages`** | `id`, `vendor_id` → `vendors`, `name`, `price`, `features_text`, `features_json`, `is_active`, `created_at`, `updated_at` |
| **`vendor_subscriptions`** | `id`, `vendor_id` → `vendors`, `plan_id` → `subscription_plans`, `starts_at`, `ends_at`, `is_active`, `created_at`, `updated_at` |

---

## Bookings / reviews

| Table | Columns |
|--------|---------|
| **`bookings`** | `id`, `customer_id` → `core_users`, `vendor_id` → `vendors`, `event_type`, `booking_date`, `location`, `amount`, `deposit`, `status`, `created_at`, `updated_at` |
| **`vendor_reviews`** | `id`, `booking_id` → `bookings`, `reviewer_id` → `core_users`, `vendor_id` → `vendors`, `rating`, `comment`, `created_at`, `updated_at` |

---

## Feed / social

| Table | Columns |
|--------|---------|
| **`posts`** | `id`, `vendor_id` → `vendors`, `caption`, `like_count`, `comment_count`, `created_at`, `updated_at` |
| **`post_media`** | `id`, `post_id` → `posts`, `url`, `is_video`, `sort_order` |
| **`post_likes`** | `id`, `post_id` → `posts`, `user_id` → `core_users`, `created_at` — unique (`post`, `user`) |
| **`comments`** | `id`, `post_id` → `posts`, `user_id` → `core_users`, `parent_id` → `comments`, `text`, `like_count`, `created_at`, `updated_at` |
| **`comment_likes`** | `id`, `comment_id` → `comments`, `user_id` → `core_users`, `created_at` — unique (`comment`, `user`) |

---

## Interactions / analytics

| Table | Columns |
|--------|---------|
| **`user_favorite_vendors`** | `id`, `user_id` → `core_users`, `vendor_id` → `vendors`, `created_at` — unique (`user`, `vendor`) |
| **`vendor_views`** | `id`, `vendor_id` → `vendors`, `user_id` → `core_users` (nullable), `viewed_at` |
| **`audit_log`** | `id`, `actor_id` → `core_users`, `action`, `resource_type`, `resource_id`, `payload`, `created_at` |

---

## Messaging / chat reports

| Table | Columns |
|--------|---------|
| **`conversations`** | `id`, `created_at`, `updated_at` |
| **`conversation_participants`** | `id`, `conversation_id` → `conversations`, `user_id` → `core_users`, `last_read_at`, `joined_at`, `left_at` — unique (`conversation`, `user`) |
| **`messages`** | `id`, `conversation_id` → `conversations`, `sender_id` → `core_users`, `text`, `attachment_url`, `created_at`, `updated_at` |
| **`message_read_receipts`** | `id`, `message_id` → `messages`, `user_id` → `core_users`, `read_at` — unique (`message`, `user`) |
| **`chat_reports`** | `id`, `conversation_id` → `conversations`, `reporter_id` → `core_users`, `reason_type`, `reason`, `status_id` → `core_statuses`, `admin_action_note`, `reviewed_by_id` → `core_users`, `reviewed_at`, `created_at`, `updated_at` |
| **`chat_report_messages`** | `id`, `report_id` → `chat_reports`, `message_id` → `messages`, `sender_id` → `core_users`, `sender_type`, `created_at` — unique (`report`, `message`) |

---

## Invitations

| Table | Columns |
|--------|---------|
| **`invitation_template_types`** | `id`, `name`, `type_key`, `description`, `sort_order`, `is_active`, `created_at`, `updated_at` |
| **`invitation_templates`** | `id`, `name`, `description`, `style`, `icon`, `invitation_type_id` → `invitation_template_types`, `sort_order`, `created_at`, `updated_at` |
| **`invitations`** | `id`, `user_id` → `core_users`, `invitation_type`, `event_type`, `template_id` → `invitation_templates`, `answers`, `created_at`, `updated_at` |

---

## Demo / example

| Table | Columns |
|--------|---------|
| **`example_items`** | `id`, `name`, `created_at` |

---

## Django framework tables (installed apps)

Because `INSTALLED_APPS` includes `django.contrib.admin`, `auth`, `contenttypes`, `sessions`, `messages`, `staticfiles`, the database also has the usual Django tables (exact names can vary slightly by backend), for example:

- `django_migrations`
- `django_content_type`
- `auth_permission`
- `django_admin_log`
- `django_session`
- `django_message` (if used)

`AUTH_USER_MODEL` is `vendly_backend.CoreUser`, so there is **no** default `auth_user` table for application users.

---

## Design note: vendor-related models

The schema includes two vendor-related concepts:

1. **`vendors`** — primary vendor entity used across listings, bookings, feed, etc.
2. **`core_vendor_profiles`** — alternate profile (`VendorProfile`) with overlapping concepts (`store_name`, `business_name`, address, etc.).

Most registration and API flows use **`vendors`** plus **`core_users`**. Treat **`core_vendor_profiles`** as legacy or unused unless your code explicitly reads/writes it.

---

## Registration data mapping (mobile)

| Who | Table | Main columns |
|-----|--------|----------------|
| Customer account | `core_users` | `first_name`, `last_name`, `email`, `phone`, `password`, `role_id` → customer role, `is_verified`, `is_active`, `created_at` |
| Vendor **person** account | `core_users` | `first_name` (vendor contact name), `last_name`, `email`, `phone`, `password`, `role_id` → vendor role, `is_verified`, … |
| Vendor **business** profile | `vendors` | `user_id` → `core_users`, **`name`** = business / storefront name, `category_id` → `categories`, `city`, `bio`, `status`, `approved_at`, … |
| Category choice | `categories` | Selected at registration; stored as `vendors.category_id` |

**Business name** is stored as **`vendors.name`** (not a separate `business_name` column). Person name uses **`core_users.first_name`** / **`last_name`**.

### OTP confirm response (`POST` confirm registration OTP)

After successful OTP, the API returns `user` with:

- **`account_type`** — e.g. `customer`, `vendor` (from `core_roles.name`).
- **Always:** core user fields (`id`, `email`, `phone`, `first_name`, `last_name`, `is_verified`, `role`, …).
- **Customers:** nested **`customer`** (`name`, `first_name`, `last_name`); **`vendor`** is `null`.
- **Vendors:** **`vendor_person_name`** (from `first_name`), nested **`vendor`** with **`business_name`** (same as `vendors.name`), `category`, `city`, `status`, `approved_at`, etc.
