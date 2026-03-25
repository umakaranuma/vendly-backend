"""
Load demo data for local development: categories, customers, vendors, listings,
feed posts, packages, subscriptions, favorites, and sample bookings/reviews.

Safe to run multiple times: existing seed users are reused; child rows are only
created when missing.

Usage:
    python manage.py seed_demo_data

Default password for all seed accounts: DemoPass123!
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from vendly_backend.booking_statuses import get_booking_status_ref
from vendly_backend.vendor_ratings import sync_vendor_rating_from_reviews
from vendly_backend.models import (
    Booking,
    Category,
    FeedComment,
    CoreRole,
    CoreStatus,
    CoreUser,
    Listing,
    Feed,
    FeedLike,
    FeedMedia,
    SubscriptionPlan,
    UserFavoriteVendor,
    Vendor,
    VendorGallery,
    VendorPackage,
    VendorReview,
    VendorSubscription,
)

SEED_PASSWORD = "DemoPass123!"

# Fixed identities so re-runs stay idempotent.
CUSTOMER_SEEDS = [
    {
        "email": "seed.customer.1@example.com",
        "phone": "+15550001001",
        "first_name": "Alex",
        "last_name": "Rivera",
    },
    {
        "email": "seed.customer.2@example.com",
        "phone": "+15550001002",
        "first_name": "Jordan",
        "last_name": "Kim",
    },
    {
        "email": "seed.customer.3@example.com",
        "phone": "+15550001003",
        "first_name": "Sam",
        "last_name": "Patel",
    },
]

VENDOR_SEEDS = [
    {
        "email": "seed.vendor.1@example.com",
        "phone": "+15550002001",
        "first_name": "Maya",
        "last_name": "Singh",
        "store_name": "Bloom & Vine Events",
        "slug": "bloom-vine-events",
        "city": "Seattle",
        "category_slug": "event-planning",
        "rating": "4.85",
        "review_count": 42,
        "price_from": "2500.00",
        "bio": "Full-service wedding and corporate event design.",
    },
    {
        "email": "seed.vendor.2@example.com",
        "phone": "+15550002002",
        "first_name": "Chris",
        "last_name": "Nguyen",
        "store_name": "Urban Lens Photography",
        "slug": "urban-lens-photography",
        "city": "Portland",
        "category_slug": "photography",
        "rating": "4.92",
        "review_count": 128,
        "price_from": "1800.00",
        "bio": "Documentary-style photography for weddings and brands.",
    },
    {
        "email": "seed.vendor.3@example.com",
        "phone": "+15550002003",
        "first_name": "Priya",
        "last_name": "Desai",
        "store_name": "Spice Route Catering",
        "slug": "spice-route-catering",
        "city": "San Francisco",
        "category_slug": "catering",
        "rating": "4.78",
        "review_count": 89,
        "price_from": "45.00",
        "bio": "Fusion menus and live stations for any size crowd.",
    },
]

CATEGORY_SEEDS = [
    {
        "name": "Event Planning",
        "slug": "event-planning",
        "description": "Coordinators, planners, and full event production.",
        "sort_order": 10,
    },
    {
        "name": "Photography",
        "slug": "photography",
        "description": "Wedding, portrait, and commercial photographers.",
        "sort_order": 20,
    },
    {
        "name": "Catering",
        "slug": "catering",
        "description": "Food, beverage, and service staff.",
        "sort_order": 30,
    },
]


def _get_or_create_user(
    *,
    email: str,
    phone: str,
    password: str,
    first_name: str,
    last_name: str,
    role: CoreRole,
    customer_status: CoreStatus,
) -> tuple[CoreUser, bool]:
    existing = CoreUser.objects.filter(email=email).first()
    if existing:
        return existing, False
    user = CoreUser.objects.create_user(
        email=email,
        phone=phone,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_verified=True,
    )
    user.status_ref = customer_status
    user.save(update_fields=["status_ref"])
    return user, True


class Command(BaseCommand):
    help = "Seed demo vendors, customers, categories, and feed-related data."

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data (password for seed users: %s)" % SEED_PASSWORD)

        customer_role, _ = CoreRole.objects.get_or_create(
            name="CUSTOMER",
            defaults={"description": "End customer"},
        )
        vendor_role, _ = CoreRole.objects.get_or_create(
            name="VENDOR",
            defaults={"description": "Vendor account"},
        )

        vendor_active, _ = CoreStatus.objects.get_or_create(
            status_type="vendor_active",
            defaults={"entity_type": "vendor", "name": "active", "sort_order": 20},
        )
        customer_active, _ = CoreStatus.objects.get_or_create(
            status_type="customer_active",
            defaults={"entity_type": "customer", "name": "active", "sort_order": 10},
        )

        with transaction.atomic():
            categories: dict[str, Category] = {}
            for c in CATEGORY_SEEDS:
                cat, _ = Category.objects.update_or_create(
                    slug=c["slug"],
                    defaults={
                        "name": c["name"],
                        "description": c["description"],
                        "sort_order": c["sort_order"],
                    },
                )
                categories[c["slug"]] = cat

            customers: list[CoreUser] = []
            for row in CUSTOMER_SEEDS:
                user, created = _get_or_create_user(
                    email=row["email"],
                    phone=row["phone"],
                    password=SEED_PASSWORD,
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    role=customer_role,
                    customer_status=customer_active,
                )
                customers.append(user)
                self.stdout.write(
                    "  customer %s - %s"
                    % (user.email, "created" if created else "already present")
                )

            vendors: list[Vendor] = []
            for row in VENDOR_SEEDS:
                user, u_created = _get_or_create_user(
                    email=row["email"],
                    phone=row["phone"],
                    password=SEED_PASSWORD,
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    role=vendor_role,
                    customer_status=customer_active,
                )
                cat = categories.get(row["category_slug"])
                vendor, v_created = Vendor.objects.get_or_create(
                    user=user,
                    defaults={
                        "name": row["store_name"],
                        "slug": row["slug"],
                        "city": row["city"],
                        "category": cat,
                        "rating": Decimal(row["rating"]),
                        "review_count": row["review_count"],
                        "price_from": Decimal(row["price_from"]),
                        "bio": row["bio"],
                        "status": "approved",
                        "status_ref": vendor_active,
                        "approved_at": timezone.now(),
                    },
                )
                if not v_created:
                    vendor.name = row["store_name"]
                    vendor.slug = row["slug"]
                    vendor.city = row["city"]
                    vendor.category = cat
                    vendor.rating = Decimal(row["rating"])
                    vendor.review_count = row["review_count"]
                    vendor.price_from = Decimal(row["price_from"])
                    vendor.bio = row["bio"]
                    vendor.status = "approved"
                    vendor.status_ref = vendor_active
                    vendor.approved_at = vendor.approved_at or timezone.now()
                    vendor.save()
                vendors.append(vendor)
                self.stdout.write(
                    "  vendor %s - %s"
                    % (vendor.name, "created" if v_created else "updated")
                )

            # Subscription plans
            starter, _ = SubscriptionPlan.objects.update_or_create(
                name="Starter",
                defaults={"max_packages": 3, "price": Decimal("29.00"), "description": "Up to 3 active packages."},
            )
            pro, _ = SubscriptionPlan.objects.update_or_create(
                name="Pro",
                defaults={"max_packages": 10, "price": Decimal("79.00"), "description": "Up to 10 active packages."},
            )

            now = timezone.now()
            for i, vendor in enumerate(vendors):
                row = VENDOR_SEEDS[i]
                plan = starter if i % 2 == 0 else pro
                if not VendorSubscription.objects.filter(vendor=vendor, plan=plan).exists():
                    VendorSubscription.objects.create(
                        vendor=vendor,
                        plan=plan,
                        starts_at=now - timedelta(days=30),
                        ends_at=now + timedelta(days=335),
                        is_active=True,
                    )

                if not VendorPackage.objects.filter(vendor=vendor, name="Essentials").exists():
                    VendorPackage.objects.create(
                        vendor=vendor,
                        name="Essentials",
                        price=Decimal(row["price_from"]),
                        features_text="Consultation, day-of coordination basics.",
                        features_json={"hours": 6, "meetings": 2},
                        is_active=True,
                    )
                if not VendorPackage.objects.filter(vendor=vendor, name="Premium").exists():
                    VendorPackage.objects.create(
                        vendor=vendor,
                        name="Premium",
                        price=Decimal("4500.00"),
                        features_text="Full planning, vendor referrals, rehearsal coverage.",
                        features_json={"hours": 12, "meetings": 5},
                        is_active=True,
                    )

            # Gallery & listings (once per vendor)
            for vendor, row in zip(vendors, VENDOR_SEEDS, strict=True):
                slug = row["slug"]
                if not vendor.gallery.exists():
                    VendorGallery.objects.bulk_create(
                        [
                            VendorGallery(
                                vendor=vendor,
                                url=f"https://picsum.photos/seed/{slug}-a/900/600",
                                sort_order=0,
                            ),
                            VendorGallery(
                                vendor=vendor,
                                url=f"https://picsum.photos/seed/{slug}-b/900/600",
                                sort_order=1,
                            ),
                        ]
                    )
                if not vendor.listings.exists():
                    Listing.objects.create(
                        vendor=vendor,
                        title=f"{row['store_name']} — Signature package",
                        description="Our most booked offering for typical events.",
                        price=Decimal(row["price_from"]),
                        category=row["category_slug"].replace("-", " ").title(),
                    )

            # Feed posts
            post_captions = [
                "Behind the scenes from last weekend’s celebration.",
                "New seasonal menu tasting — book a sample session.",
                "Golden hour portraits from the waterfront venue.",
            ]
            for vendor, row, cap in zip(vendors, VENDOR_SEEDS, post_captions, strict=True):
                slug = row["slug"]
                if not vendor.feeds.exists():
                    feed = Feed.objects.create(vendor=vendor, caption=cap, like_count=2, comment_count=1)
                    FeedMedia.objects.create(
                        feed=feed,
                        url=f"https://picsum.photos/seed/{slug}-post/1080/1080",
                        is_video=False,
                        sort_order=0,
                    )

            # Likes & comments (first customer interacts with first post of each vendor)
            customer_a = customers[0]
            for vendor in vendors:
                feed = vendor.feeds.order_by("id").first()
                if feed:
                    FeedLike.objects.get_or_create(feed=feed, user=customer_a)
                    if not feed.comments.filter(created_by=customer_a).exists():
                        FeedComment.objects.create(
                            feed=feed,
                            created_by=customer_a,
                            comment="This looks amazing — saving for our date!",
                        )

            # Favorites
            if len(customers) >= 2 and len(vendors) >= 2:
                UserFavoriteVendor.objects.get_or_create(user=customers[0], vendor=vendors[0])
                UserFavoriteVendor.objects.get_or_create(user=customers[1], vendor=vendors[1])

            # Booking + review (completed flow) for first vendor
            v0 = vendors[0]
            booking = Booking.objects.filter(customer=customer_a, vendor=v0).first()
            if not booking:
                booking = Booking.objects.create(
                    customer=customer_a,
                    requested_by=customer_a,
                    vendor=v0,
                    event_type="Wedding reception",
                    booking_date=now - timedelta(days=14),
                    location=v0.city,
                    amount=Decimal("5200.00"),
                    deposit=Decimal("1000.00"),
                    status=get_booking_status_ref("completed"),
                )
            if not VendorReview.objects.filter(booking=booking).exists():
                VendorReview.objects.create(
                    booking=booking,
                    reviewer=customer_a,
                    vendor=v0,
                    rating=Decimal("5.00"),
                    comment="Flawless execution and great communication.",
                )
            sync_vendor_rating_from_reviews(v0.id)

        self.stdout.write(self.style.SUCCESS("Demo seed finished."))
