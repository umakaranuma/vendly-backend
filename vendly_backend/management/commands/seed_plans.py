from django.core.management.base import BaseCommand
from vendly_backend.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Seed subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Starter',
                'price': 0.00,
                'max_packages': 2,
                'description': 'Basic analytics, 2 pricing packages, single vendor profile.'
            },
            {
                'name': 'Professional',
                'price': 1500.00,
                'max_packages': 10,
                'description': 'Audience locations, orders breakdown, 10 pricing packages.'
            },
            {
                'name': 'Premium',
                'price': 4500.00,
                'max_packages': 100,
                'description': 'Full analytics suite, engagement metrics, multi-vendor management.'
            }
        ]

        for p in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=p['name'],
                defaults=p
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Updated plan: {plan.name}"))

        self.stdout.write(self.style.SUCCESS("Successfully seeded subscription plans."))
