import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from vendly_backend.models import (
    CoreUser, CoreRole, CoreStatus, VendorProfile, Vendor, Category,
    VendorGallery, Listing, SubscriptionPlan, VendorPackage,
    VendorSubscription, Booking, VendorReview, Feed, FeedMedia,
    FeedLike, FeedComment, UserFavoriteVendor, VendorFollower,
    VendorView, AuditLog, Conversation, ConversationParticipant,
    Message, MessageReadReceipt, Invitation, InvitationTemplate
)

class Command(BaseCommand):
    help = "Seed sample business data (vendors, customers, feed, etc.)."

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample data...")

        try:
            customer_role = CoreRole.objects.get(name="CUSTOMER")
            vendor_role = CoreRole.objects.get(name="VENDOR")
            vendor_approved_status = CoreStatus.objects.get(status_type="vendor_approved")
            customer_active_status = CoreStatus.objects.get(status_type="customer_active")
            booking_completed_status = CoreStatus.objects.get(status_type="booking_completed")
            booking_pending_status = CoreStatus.objects.get(status_type="booking_pending")
        except CoreRole.DoesNotExist:
            self.stdout.write(self.style.ERROR("Roles/Statuses not found. Run 'python manage.py seed_admin' first."))
            return

        with transaction.atomic():
            # 1. Create Customers
            customers = []
            for i in range(1, 6):
                email = f"customer{i}@example.com"
                user, created = CoreUser.objects.get_or_create(
                    email=email,
                    defaults={
                        "phone": f"+1555100000{i}",
                        "first_name": f"Customer",
                        "last_name": str(i),
                        "role": customer_role,
                        "status_ref": customer_active_status,
                        "is_verified": True
                    }
                )
                if created:
                    user.set_password("Pass123!")
                    user.save()
                    self.stdout.write(f"  Created customer: {email}")
                customers.append(user)

            # 2. Create Vendors
            categories = list(Category.objects.all())
            plans = list(SubscriptionPlan.objects.all())
            vendors = []
            for i in range(1, 6):
                email = f"vendor{i}@example.com"
                user, created = CoreUser.objects.get_or_create(
                    email=email,
                    defaults={
                        "phone": f"+1555200000{i}",
                        "first_name": f"Vendor",
                        "last_name": str(i),
                        "role": vendor_role,
                        "status_ref": customer_active_status,
                        "is_verified": True
                    }
                )
                if created:
                    user.set_password("Pass123!")
                    user.save()
                    self.stdout.write(f"  Created vendor user: {email}")
                
                # Profile
                profile, _ = VendorProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "store_name": f"Store {i}",
                        "business_name": f"Business {i} LLC",
                        "city": "Remote",
                        "is_approved": True
                    }
                )
                
                # Vendor Entity
                vendor, v_created = Vendor.objects.get_or_create(
                    user=user,
                    defaults={
                        "name": f"Store {i}",
                        "slug": f"store-{i}",
                        "category": random.choice(categories) if categories else None,
                        "status": "approved",
                        "status_ref": vendor_approved_status,
                        "approved_at": timezone.now()
                    }
                )
                if v_created:
                    self.stdout.write(f"  Created vendor: {vendor.name}")
                vendors.append(vendor)

                # Gallery
                if v_created:
                    VendorGallery.objects.create(vendor=vendor, url=f"https://picsum.photos/seed/v{i}g1/800/600", sort_order=1)
                    VendorGallery.objects.create(vendor=vendor, url=f"https://picsum.photos/seed/v{i}g2/800/600", sort_order=2)

                # Packages
                package, _ = VendorPackage.objects.get_or_create(
                    vendor=vendor,
                    name="Standard Package",
                    defaults={"price": Decimal("500.00"), "features_text": "Feature 1, Feature 2"}
                )

                # Subscription
                if plans:
                    VendorSubscription.objects.get_or_create(
                        vendor=vendor,
                        plan=random.choice(plans),
                        defaults={"starts_at": timezone.now(), "is_active": True}
                    )

                # Feed Post
                feed, _ = Feed.objects.get_or_create(
                    vendor=vendor,
                    caption=f"Exited to show our latest work at Store {i}!",
                    defaults={"like_count": 0, "comment_count": 0}
                )
                FeedMedia.objects.get_or_create(feed=feed, url=f"https://picsum.photos/seed/v{i}f/1080/1080")

            # 3. Interactions & Data
            for customer in customers:
                # Favorites & Follows
                target_vendor = random.choice(vendors)
                UserFavoriteVendor.objects.get_or_create(user=customer, vendor=target_vendor)
                VendorFollower.objects.get_or_create(user=customer, vendor=target_vendor)
                VendorView.objects.create(vendor=target_vendor, user=customer)

                # Bookings
                v = random.choice(vendors)
                pkg = v.packages.first()
                Booking.objects.create(
                    customer=customer,
                    requested_by=customer,
                    vendor=v,
                    vendor_package=pkg,
                    event_type="Seeded Event",
                    booking_date=timezone.now() + timedelta(days=30),
                    amount=pkg.price if pkg else Decimal("0.00"),
                    status=booking_pending_status
                )

                # Completed Booking + Review
                v_rev = random.choice(vendors)
                pkg_rev = v_rev.packages.first()
                booking_done = Booking.objects.create(
                    customer=customer,
                    requested_by=customer,
                    vendor=v_rev,
                    vendor_package=pkg_rev,
                    event_type="Past Event",
                    booking_date=timezone.now() - timedelta(days=30),
                    amount=pkg_rev.price if pkg_rev else Decimal("100.00"),
                    status=booking_completed_status
                )
                VendorReview.objects.create(
                    booking=booking_done,
                    reviewer=customer,
                    vendor=v_rev,
                    rating=Decimal("5.0"),
                    comment="Excellent service!"
                )

            # 4. Conversations
            for i in range(3):
                cust = customers[i]
                vend = vendors[i]
                conv = Conversation.objects.create()
                ConversationParticipant.objects.create(conversation=conv, user=cust)
                ConversationParticipant.objects.create(conversation=conv, user=vend.user)
                
                msg = Message.objects.create(conversation=conv, sender=cust, text="Hello! I'm interested in your services.")
                MessageReadReceipt.objects.create(message=msg, user=vend.user)
                Message.objects.create(conversation=conv, sender=vend.user, text="Hi! How can I help you today?")

            # 5. Invitations
            inv_tpl = InvitationTemplate.objects.first()
            if inv_tpl:
                Invitation.objects.create(
                    user=customers[0],
                    invitation_type="Digital",
                    event_type="Anniversary",
                    template=inv_tpl,
                    answers={"name": "Alex & Sam", "date": "2026-12-31"}
                )

            # 6. Audit Log
            AuditLog.objects.create(
                actor=customers[0],
                action="seeded_dummy_data",
                resource_type="system"
            )

        self.stdout.write(self.style.SUCCESS("Sample data seeding completed successfully."))
