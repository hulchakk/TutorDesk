import uuid
from typing import TYPE_CHECKING

from django.contrib.auth.models import (
    AbstractUser,
    BaseUserManager,
)
from django.db import models
from django.utils.translation import gettext as _


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_teacher(self, email, password, **extra_fields):
        """Create and save a teacher User with the given email and password."""
        extra_fields.setdefault("is_teacher", True)
        extra_fields.setdefault("is_student", False)
        return self.create_user(email, password, **extra_fields)

    def create_student(self, email, password, **extra_fields):
        """Create and save a student User with the given email and password."""
        extra_fields.setdefault("is_student", True)
        extra_fields.setdefault("is_teacher", False)
        return self.create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None

    email = models.EmailField(_("email address"), unique=True, null=False)

    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)

    name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.name} - {self.email}"


class InviteToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student_profile = models.OneToOneField(
        "schedule.Student", on_delete=models.CASCADE, related_name="invite_token"
    )

    created_at = models.DateTimeField(auto_now_add=True)
