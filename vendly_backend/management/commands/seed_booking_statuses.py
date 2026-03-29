from django.core.management.base import BaseCommand
from vendly_backend.models.core import CoreStatus

class Command(BaseCommand):
    help = "Seed booking statuses into core_statuses table"

    def handle(self, *args, **options):
        statuses = [
            {
                "entity_type": "booking",
                "name": "Requested",
                "status_type": "booking_requested",
                "sort_order": 1,
            },
            {
                "entity_type": "booking",
                "name": "Pending",
                "status_type": "booking_pending",
                "sort_order": 2,
            },
            {
                "entity_type": "booking",
                "name": "Accepted",
                "status_type": "booking_accepted",
                "sort_order": 3,
            },
            {
                "entity_type": "booking",
                "name": "Completed",
                "status_type": "booking_completed",
                "sort_order": 4,
            },
            {
                "entity_type": "booking",
                "name": "Canceled",
                "status_type": "booking_cancelled",
                "sort_order": 5,
            },
        ]

        for s in statuses:
            obj, created = CoreStatus.objects.update_or_create(
                status_type=s["status_type"],
                defaults={
                    "entity_type": s["entity_type"],
                    "name": s["name"],
                    "sort_order": s["sort_order"],
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created status: {s['name']} ({s['status_type']})"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Updated status: {s['name']} ({s['status_type']})"))

        self.stdout.write(self.style.SUCCESS("Booking statuses seeded successfully."))
