from django.core.management.base import BaseCommand
from django.db import transaction
from vendly_backend.models import CoreRole, CoreStatus, CoreUser

class Command(BaseCommand):
    help = "Seed core roles, statuses, and admin users."

    def handle(self, *args, **options):
        self.stdout.write("Seeding admin data...")

        with transaction.atomic():
            # 1. Roles
            roles = [
                ("ADMIN", "System Administrator with full access"),
                ("VENDOR", "Vendor with access to manage their own store and listings"),
                ("CUSTOMER", "Regular user who can browse and book vendors"),
            ]
            for name, desc in roles:
                role, created = CoreRole.objects.get_or_create(name=name, defaults={"description": desc})
                if created:
                    self.stdout.write(f"  Created role: {name}")

            # 2. Statuses
            statuses = [
                # Vendors
                ("vendor", "pending", "vendor_pending", 10),
                ("vendor", "approved", "vendor_approved", 20),
                ("vendor", "rejected", "vendor_rejected", 30),
                ("vendor", "suspended", "vendor_suspended", 40),
                # Customers
                ("customer", "active", "customer_active", 10),
                ("customer", "inactive", "customer_inactive", 20),
                ("customer", "blocked", "customer_blocked", 30),
                # Bookings
                ("booking", "pending", "booking_pending", 10),
                ("booking", "confirmed", "booking_confirmed", 20),
                ("booking", "completed", "booking_completed", 30),
                ("booking", "cancelled", "booking_cancelled", 40),
            ]
            for entity, name, s_type, order in statuses:
                status, created = CoreStatus.objects.get_or_create(
                    status_type=s_type,
                    defaults={"entity_type": entity, "name": name, "sort_order": order}
                )
                if created:
                    self.stdout.write(f"  Created status: {s_type}")

            # 3. Superuser & Admin
            admin_role = CoreRole.objects.get(name="ADMIN")
            
            if not CoreUser.objects.filter(email="admin@vendly.app").exists():
                admin_user = CoreUser.objects.create_superuser(
                    email="admin@vendly.app",
                    password="AdminPass123!",
                    first_name="Super",
                    last_name="Admin",
                    role=admin_role,
                )
                self.stdout.write("  Created superuser: admin@vendly.app")

            if not CoreUser.objects.filter(email="staff@vendly.app").exists():
                staff_user = CoreUser.objects.create_user(
                    email="staff@vendly.app",
                    password="StaffPass123!",
                    first_name="Staff",
                    last_name="Member",
                    is_staff=True,
                    role=admin_role,
                )
                self.stdout.write("  Created staff user: staff@vendly.app")

        self.stdout.write(self.style.SUCCESS("Admin seeding completed successfully."))
