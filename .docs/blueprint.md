# Vendly Mobile – Project Blueprint

## Overview

**Vendly Mobile** is a Flutter-based celebrations and events platform that connects consumers with vendors (photographers, planners, makeup artists, décor specialists, musicians, etc.). The app supports three roles: **Customer**, **Vendor**, and **Admin**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile Framework | Flutter |
| Routing | GoRouter |
| Dependency Injection | GetIt |
| HTTP Client | Dio (future API) |
| Local Storage | SharedPreferences (auth/session) |
| Auth | Bearer token via `Authorization` header |

---

## Environment Base URLs

| Mode | Main API (`candidateBaseUrl`) | Identity (`idpBaseUrl`) |
|---|---|---|
| debug | `https://dev-admin.joboro.apptimus.lk/api/candidates` | `https://idp-ui.utilities.apptimus.lk/idp-api/api/` |
| demo | `https://demo-api.empowerone.io/passenger/api/` | same |
| test | `https://test-api.empowerone.io/passenger/api/` | same |
| uat | `https://uat-api.empowerone.io/passenger/api/` | same |
| live | `https://live-api.empowerone.io/passenger/api/` | same |

---

## User Roles

| Role | Description |
|---|---|
| Customer | Discovers vendors, browses feed, books services, chats, creates invitations |
| Vendor | Manages listings, posts, bookings, views analytics |
| Admin | Backend-only: manages users, vendors, categories, posts, reviews, subscriptions |

---

## Application Flow

```
Splash (/)
  └── Onboarding (/onboarding)
        ├── Register (/register)
        └── Login (/login)
              └── Home (/home)
                    ├── Feed/Discover
                    │     ├── Search (/search)
                    │     └── Vendor Profile (/vendors/profile)
                    ├── Vendors List → Vendor Profile
                    ├── Likes (/likes)
                    ├── Bookings
                    │     ├── Customer: in-shell
                    │     └── Vendor: /vendor/bookings → /vendor/booking/detail
                    └── Messages → Chat (/chat)

Profile (/profile)
  ├── Edit Profile (/profile/edit)
  ├── Notifications
  ├── Language & Region
  ├── Help & FAQ
  ├── Privacy & Security
  └── Invitations (/invitations)
        └── Create (/invitations/create)
              └── Choose Template (/invitations/create/choose-template)

Vendor-Only Routes:
  /vendor/listings
  /vendor/posts → /vendor/posts/create
  /vendor/bookings → /vendor/booking/detail
  /vendor/analytics
```

---

## Module Breakdown

### Auth Module
- Register, Login, Logout
- Role-based routing (customer/vendor)
- Bearer token stored via `AuthDataSources`
- 401 handler → auto-logout

### Customer Module
- **Feed (Discover):** Post cards (image/video), like, comment, share
- **Search:** Recent searches, category chips, vendor search results
- **Vendors:** Filter by category/price, browse vendor profiles
- **Likes:** List of favorited vendors
- **Bookings:** View and filter bookings (All / Upcoming / Completed / Cancelled)
- **Messages:** Conversation list + full chat UI
- **Profile:** View/edit profile, notification settings, language, theme, help, privacy
- **Invitations:** Create and manage text/video/website invitations with templates

### Vendor Module
- **Listings:** Manage service offerings
- **Posts:** Create and manage feed posts
- **Bookings:** View bookings (Pending / Confirmed / Completed / Cancelled), booking detail with calendar
- **Analytics:** Dashboard with views, likes, bookings, revenue
- **Packages:** Create custom service packages (limited by subscription plan)

### Admin Module (Backend Only)
- User management (list, view, update, role change)
- Vendor approval/rejection/suspension
- Post moderation (delete)
- Category CRUD
- Booking overview
- Conversation moderation
- Review deletion
- Subscription plan management

---

## Auth Flow

```
Register/Login
  → POST auth/register or auth/login
  → Receive { user, token }
  → Store token + user + role in SharedPreferences
  → Navigate to /home

On 401 response:
  → Clear session (AuthDataSources)
  → Redirect to /login

Logout:
  → POST auth/logout (Bearer)
  → Clear local session
  → Redirect to /onboarding
```

---

## Key Business Rules

1. **Vendor approval:** Vendors require admin approval (`status = 'approved'`) before appearing in search results and vendor lists.
2. **Reviews:** A review can only be submitted against a **completed** booking. One review per booking. Admin can delete any review.
3. **Package limits:** The number of active vendor packages is capped by the vendor's active subscription plan (`subscription_plans.max_packages`). Default free plan allows 2 packages.
4. **Messaging:** Starting a conversation with the same user/vendor is idempotent — existing conversation is returned.
5. **File upload:** Media (avatar, cover, post images) is uploaded via `POST upload-file` (multipart), returning a CDN/S3 URL.

---

## Current State vs. Target

| Area | Current State | Target |
|---|---|---|
| Auth | SharedPreferences only, no API calls | IDP API integration |
| Feed | Mock data | Live API (`feed/posts`) |
| Vendors | Mock data | Live API (`vendors`) |
| Bookings | Mock data | Live API (`bookings`) |
| Messages | Mock data | Live API + real-time WebSocket/polling |
| Invitations | Mock templates | Live API (`invitations`, `invitations/templates`) |
| File Upload | Commented out | POST `upload-file` multipart |
| Analytics | Mock data | Aggregated live API |

---

*Blueprint generated from `FEATURES_APIS_AND_DATABASE.md`. Update when new features or architecture changes are introduced.*
