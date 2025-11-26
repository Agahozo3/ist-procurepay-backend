from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
from django.utils import timezone

# ---------------------------
# User Manager
# ---------------------------
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, role='staff', **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        if role not in ['staff', 'approver', 'finance']:
            raise ValueError("Role must be one of: staff, approver, finance")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, role='staff', **extra_fields)

# ---------------------------
# User Model
# ---------------------------
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('approver', 'Approver'),
        ('finance', 'Finance'),
    ]

    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

# ---------------------------
# Request Model
# ---------------------------
class Request(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),              
        ('APPROVED', 'Approved'),           
        ('REJECTED', 'Rejected'),            
        ('RECEIPT_UPLOADED', 'Receipt Uploaded'),  
        ('PAID', 'Paid'),                    
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Relationships
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requests'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests'
    )
    finance_uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_uploaded_requests'
    )

    # File uploads
    proforma = models.FileField(upload_to='proformas/', null=True, blank=True)
    purchase_order = models.FileField(upload_to='purchase_orders/', null=True, blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)

    # Optional finance notes
    payment_date = models.DateField(null=True, blank=True)
    payment_notes = models.TextField(blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"
