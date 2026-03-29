from django.core.management.base import BaseCommand
from vendly_backend.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Seed subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Free',
                'price': 0.00,
                'max_packages': 1,
                'description': 'Baseline analytics, 1 pricing package, standard profile visibility.'
            },
            {
                'name': 'Starter',
                'price': 1500.00,
                'max_packages': 5,
                'description': 'Advanced analytics including order breakdowns, up to 5 pricing packages.'
            },
            {
                'name': 'Premium',
                'price': 4500.00,
                'max_packages': 50,
                'description': 'Full analytics suite with audience location insights, priority support, and up to 50 pricing packages.'
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
