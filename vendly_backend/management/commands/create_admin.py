from django.core.management.base import BaseCommand
from vendly_backend.models import CoreRole, CoreUser

class Command(BaseCommand):
    help = "Create an admin user with email and password."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Email for the admin user")
        parser.add_argument("password", type=str, help="Password for the admin user")
        parser.add_argument("--first_name", type=str, default="Admin", help="First name")
        parser.add_argument("--last_name", type=str, default="User", help="Last name")

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]
        first_name = options["first_name"]
        last_name = options["last_name"]

        try:
            admin_role = CoreRole.objects.get(name="ADMIN")
        except CoreRole.DoesNotExist:
            self.stdout.write(self.style.ERROR("ADMIN role not found. Please run 'python manage.py seed_admin' first."))
            return

        if CoreUser.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"User with email {email} already exists."))
            return

        user = CoreUser.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=admin_role,
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully created admin user: {email}"))
