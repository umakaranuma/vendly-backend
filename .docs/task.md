# Vendly Mobile – Development Task List

> This document tracks all development tasks required to bring the Vendly Mobile app from its current mock/local state to full backend integration.

---

## Status Legend

| Symbol | Meaning |
|---|---|
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | Done |

---

## Module 1: Authentication

| # | Task | Priority | Status |
|---|---|---|---|
| 1.1 | Implement `POST auth/register` API call | High | ⬜ |
| 1.2 | Implement `POST auth/login` API call | High | ⬜ |
| 1.3 | Implement `POST auth/logout` API call | High | ⬜ |
| 1.4 | Wire `AuthRepository` in `service_locator.dart` (currently commented out) | High | ⬜ |
| 1.5 | Replace SharedPreferences mock with real token/user from API response | High | ⬜ |
| 1.6 | Implement 401 interceptor in Dio → auto-logout handler | High | ⬜ |
| 1.7 | Implement `POST auth/forgot-password` | Medium | ⬜ |
| 1.8 | Add "Forgot password?" link on Login screen | Medium | ⬜ |

---

## Module 2: Profile

| # | Task | Priority | Status |
|---|---|---|---|
| 2.1 | Implement `GET users/me` to load profile data | High | ⬜ |
| 2.2 | Implement `PUT users/me` to save profile edits | High | ⬜ |
| 2.3 | Uncomment and wire `file_upload_datasourses.dart` | High | ⬜ |
| 2.4 | Implement `POST upload-file` (multipart) for avatar upload | High | ⬜ |
| 2.5 | Implement `POST upload-file` for cover photo upload | High | ⬜ |

---

## Module 3: Feed (Discover)

| # | Task | Priority | Status |
|---|---|---|---|
| 3.1 | Replace mock feed data with `GET feed/posts?page=&limit=` | High | ⬜ |
| 3.2 | Implement `POST feed/posts/:id/like` | High | ⬜ |
| 3.3 | Implement `DELETE feed/posts/:id/like` | High | ⬜ |
| 3.4 | Implement `GET feed/posts/:id/comments` | High | ⬜ |
| 3.5 | Implement `POST feed/posts/:id/comments` (with optional `parent_id`) | High | ⬜ |
| 3.6 | Implement `POST feed/comments/:id/like` | Medium | ⬜ |
| 3.7 | Add infinite scroll / pagination to feed | Medium | ⬜ |

---

## Module 4: Search & Vendors

| # | Task | Priority | Status |
|---|---|---|---|
| 4.1 | Replace mock vendor list with `GET vendors?q=&category_id=&min_price=&max_price=&page=&limit=` | High | ⬜ |
| 4.2 | Implement `GET vendors/:id` for vendor profile screen | High | ⬜ |
| 4.3 | Implement `GET search/suggestions?q=` for search bar | Medium | ⬜ |
| 4.4 | Implement `GET categories` to populate category filters | High | ⬜ |
| 4.5 | Implement `GET vendors/:vendor_id/packages` to show packages on vendor profile | Medium | ⬜ |
| 4.6 | Implement `GET vendors/:id/reviews` to show reviews on vendor profile | Medium | ⬜ |

---

## Module 5: Favorites

| # | Task | Priority | Status |
|---|---|---|---|
| 5.1 | Replace mock likes list with `GET users/me/favorites` | High | ⬜ |
| 5.2 | Implement `POST vendors/:id/favorite` | High | ⬜ |
| 5.3 | Implement `DELETE vendors/:id/favorite` | High | ⬜ |

---

## Module 6: Bookings (Customer)

| # | Task | Priority | Status |
|---|---|---|---|
| 6.1 | Replace mock bookings with `GET bookings?status=&page=&limit=` | High | ⬜ |
| 6.2 | Implement `GET bookings/:id` for booking detail | High | ⬜ |
| 6.3 | Implement `POST bookings` to create a new booking from vendor profile | High | ⬜ |
| 6.4 | Implement booking cancellation via `PATCH bookings/:id` with `status: cancelled` | Medium | ⬜ |

---

## Module 7: Vendor Reviews

| # | Task | Priority | Status |
|---|---|---|---|
| 7.1 | Implement `POST vendors/:id/reviews` (with booking_id, rating, comment) | High | ⬜ |
| 7.2 | Enforce "completed booking" check before showing review button | High | ⬜ |
| 7.3 | Show average rating and review list on vendor profile | Medium | ⬜ |

---

## Module 8: Messages & Chat

| # | Task | Priority | Status |
|---|---|---|---|
| 8.1 | Replace mock conversation list with `GET conversations` | High | ⬜ |
| 8.2 | Implement `POST conversations` to start a new chat from vendor profile | High | ⬜ |
| 8.3 | Implement `GET conversations/:id/messages` with cursor pagination | High | ⬜ |
| 8.4 | Implement `POST conversations/:id/messages` to send text messages | High | ⬜ |
| 8.5 | Implement `PATCH conversations/:id/read` to mark messages as read | Medium | ⬜ |
| 8.6 | Implement attachment sending (multipart file upload in chat) | Low | ⬜ |
| 8.7 | Evaluate and implement real-time updates (WebSocket / polling) | Medium | ⬜ |

---

## Module 9: Invitations

| # | Task | Priority | Status |
|---|---|---|---|
| 9.1 | Replace mock templates with `GET invitations/templates?type=` | High | ⬜ |
| 9.2 | Implement `POST invitations` to save a new invitation | High | ⬜ |
| 9.3 | Replace mock invitation list with `GET invitations` | High | ⬜ |
| 9.4 | Implement `GET invitations/:id` for invitation detail | Medium | ⬜ |
| 9.5 | Implement `DELETE invitations/:id` | Medium | ⬜ |

---

## Module 10: Vendor – Listings & Posts

| # | Task | Priority | Status |
|---|---|---|---|
| 10.1 | Replace mock listings with `GET vendors/me/listings` | High | ⬜ |
| 10.2 | Implement `POST vendors/me/listings` to create a listing | High | ⬜ |
| 10.3 | Implement `PUT vendors/me/listings/:id` to edit a listing | Medium | ⬜ |
| 10.4 | Implement `DELETE vendors/me/listings/:id` | Medium | ⬜ |
| 10.5 | Replace mock posts with `GET vendors/me/posts` | High | ⬜ |
| 10.6 | Implement `POST vendors/me/posts` (with media upload) | High | ⬜ |
| 10.7 | Implement `DELETE vendors/me/posts/:id` | Medium | ⬜ |

---

## Module 11: Vendor – Packages & Subscriptions

| # | Task | Priority | Status |
|---|---|---|---|
| 11.1 | Implement `GET vendors/me/packages` | High | ⬜ |
| 11.2 | Implement `POST vendors/me/packages` (with max_packages limit check) | High | ⬜ |
| 11.3 | Implement `PUT vendors/me/packages/:id` | Medium | ⬜ |
| 11.4 | Implement `DELETE vendors/me/packages/:id` | Medium | ⬜ |
| 11.5 | Implement `GET vendors/me/subscription` to show current plan | Medium | ⬜ |
| 11.6 | Implement `GET subscription/plans` for plan listing | Low | ⬜ |

---

## Module 12: Vendor – Bookings

| # | Task | Priority | Status |
|---|---|---|---|
| 12.1 | Replace mock vendor bookings with `GET bookings?status=` (vendor-scoped) | High | ⬜ |
| 12.2 | Implement `GET bookings/:id` for vendor booking detail screen | High | ⬜ |
| 12.3 | Implement confirm booking via `PATCH bookings/:id` with `status: confirmed` | High | ⬜ |
| 12.4 | Implement complete booking via `PATCH bookings/:id` with `status: completed` | High | ⬜ |

---

## Module 13: Vendor – Analytics

| # | Task | Priority | Status |
|---|---|---|---|
| 13.1 | Replace mock analytics with `GET vendors/me/analytics?from=&to=` | Medium | ⬜ |
| 13.2 | Render chart data from API response | Medium | ⬜ |

---

## Module 14: Notifications

| # | Task | Priority | Status |
|---|---|---|---|
| 14.1 | Implement `GET users/me/notifications?page=&limit=` | Medium | ⬜ |
| 14.2 | Implement `PATCH users/me/notifications/:id/read` | Medium | ⬜ |
| 14.3 | Implement `PATCH users/me/notification-settings` | Low | ⬜ |

---

## Module 15: Admin (Backend)

| # | Task | Priority | Status |
|---|---|---|---|
| 15.1 | Implement admin user management endpoints (list, view, update) | High | ⬜ |
| 15.2 | Implement vendor approval/rejection endpoints | High | ⬜ |
| 15.3 | Implement category CRUD endpoints | High | ⬜ |
| 15.4 | Implement admin review deletion | Medium | ⬜ |
| 15.5 | Implement admin post/message moderation endpoints | Medium | ⬜ |
| 15.6 | Implement subscription plan management (admin) | Medium | ⬜ |
| 15.7 | Implement vendor subscription assignment (admin) | Medium | ⬜ |
| 15.8 | (Optional) Implement audit_log table and logging for admin actions | Low | ⬜ |

---

## Infrastructure & Cross-cutting

| # | Task | Priority | Status |
|---|---|---|---|
| I.1 | Set up Dio base options and interceptors (auth header, 401 handler) | High | ⬜ |
| I.2 | Configure environment-based base URLs in `env_config.dart` | High | ⬜ |
| I.3 | Wire all repositories in `service_locator.dart` (currently commented out) | High | ⬜ |
| I.4 | Implement global error handling and user-facing error messages | Medium | ⬜ |
| I.5 | Implement loading states across all data-fetching screens | Medium | ⬜ |
| I.6 | Implement pagination/infinite scroll consistently across all list screens | Medium | ⬜ |
| I.7 | Add unit and widget tests for repositories and key UI flows | Low | ⬜ |

---

*Task list generated from `FEATURES_APIS_AND_DATABASE.md`. Update task statuses and add new tasks as development progresses.*
