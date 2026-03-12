from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class CoreRole(models.Model):
    """
    Simple role model for customers, vendors, and admins.
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_roles"

    def __str__(self) -> str:
        return self.name


class CoreUserManager(BaseUserManager):
    def _create_user(self, email: str | None, phone: str | None, password: str | None, **extra_fields):
        if not email and not phone:
            raise ValueError("The user must have either an email or phone.")

        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str | None = None, phone: str | None = None, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, phone, password, **extra_fields)

    def create_superuser(self, email: str | None = None, phone: str | None = None, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, phone, password, **extra_fields)


class CoreUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model backed by `core_users` table.
    """

    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    role = models.ForeignKey(CoreRole, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CoreUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "core_users"
        app_label = "vendly_backend"

    def __str__(self) -> str:
        identifier = self.email or self.phone or str(self.pk)
        return f"{identifier}"


class VendorProfile(models.Model):
    """
    Vendor-specific profile attached to a CoreUser.
    """

    user = models.OneToOneField(CoreUser, on_delete=models.CASCADE, related_name="vendor_profile")
    store_name = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    contact_email = models.EmailField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    is_approved = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_vendor_profiles"
        app_label = "vendly_backend"

    def __str__(self) -> str:
        return self.store_name

