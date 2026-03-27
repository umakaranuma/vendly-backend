from django.core.management.base import BaseCommand
from django.db import transaction
from vendly_backend.models import Category, SubscriptionPlan, InvitationTemplateType, InvitationTemplate

class Command(BaseCommand):
    help = "Seed application configuration (categories, plans, templates)."

    def handle(self, *args, **options):
        self.stdout.write("Seeding app configuration...")

        with transaction.atomic():
            # 1. Categories
            categories = [
                ("Photography", "photography", "Professional wedding and event photographers", 10),
                ("Catering", "catering", "Food and beverage services for events", 20),
                ("Venue", "venue", "Event spaces and locations", 30),
                ("Music & DJ", "music-dj", "Live bands, DJs, and sound services", 40),
                ("Decor & Florist", "decor-florist", "Event decoration and floral arrangements", 50),
                ("Wedding Planning", "wedding-planning", "Full wedding planning and coordination", 60),
                ("Makeup & Hair", "makeup-hair", "Beauty services for brides and guests", 70),
                ("Videography", "videography", "Event filming and editing", 80),
            ]
            for name, slug, desc, order in categories:
                cat, created = Category.objects.get_or_create(
                    slug=slug,
                    defaults={"name": name, "description": desc, "sort_order": order}
                )
                if created:
                    self.stdout.write(f"  Created category: {name}")

            # 2. Subscription Plans
            plans = [
                ("Free", 1, 0.00, "Basic plan for new vendors"),
                ("Starter", 3, 29.00, "Up to 3 active packages"),
                ("Pro", 10, 79.00, "Up to 10 active packages"),
                ("Enterprise", 50, 199.00, "Unlimited packages and premium support"),
            ]
            for name, max_pkg, price, desc in plans:
                plan, created = SubscriptionPlan.objects.get_or_create(
                    name=name,
                    defaults={"max_packages": max_pkg, "price": price, "description": desc}
                )
                if created:
                    self.stdout.write(f"  Created plan: {name}")

            # 3. Invitation Template Types
            types = [
                ("Wedding", "wedding", "Wedding invitations and save the dates", 10),
                ("Birthday", "birthday", "Birthday party invitations", 20),
                ("Corporate", "corporate", "Business events and conferences", 30),
                ("Social", "social", "General social gatherings", 40),
            ]
            for name, key, desc, order in types:
                t_type, created = InvitationTemplateType.objects.get_or_create(
                    type_key=f"template_{key}",
                    defaults={"name": name, "description": desc, "sort_order": order}
                )
                if created:
                    self.stdout.write(f"  Created invitation type: {name}")

            # 4. Invitation Templates
            wedding_type = InvitationTemplateType.objects.get(type_key="template_wedding")
            templates = [
                ("Classic Elegance", "Classic white and gold theme", "classic", "stars", wedding_type, 10),
                ("Modern Minimalist", "Clean lines and bold typography", "modern", "square", wedding_type, 20),
                ("Rustic Charm", "Natural tones and floral accents", "rustic", "feather", wedding_type, 30),
            ]
            for name, desc, style, icon, t_type, order in templates:
                tpl, created = InvitationTemplate.objects.get_or_create(
                    name=name,
                    defaults={
                        "description": desc,
                        "style": style,
                        "icon": icon,
                        "invitation_type": t_type,
                        "sort_order": order
                    }
                )
                if created:
                    self.stdout.write(f"  Created template: {name}")

        self.stdout.write(self.style.SUCCESS("App configuration seeding completed successfully."))
