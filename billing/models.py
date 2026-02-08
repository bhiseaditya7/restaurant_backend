from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models

import uuid
from django.db import transaction
from cloudinary.models import CloudinaryField


class UserManager(BaseUserManager):
    def create_user(self, phone_number, email=None, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")

        email = self.normalize_email(email)
        user = self.model(phone_number=phone_number, email=email, **extra_fields)
        user.set_unusable_password() # Users authenticate via OTP, so no password is set
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone_number, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'."
            )
        ]
    )

    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["email", "name"]

    def __str__(self):
        return f"{self.phone_number} - {self.name}"

class Menu(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    price = models.DecimalField(max_digits=8, decimal_places=2) 
    is_vegetarian = models.BooleanField(default=True)
    rating = models.FloatField(default=0.0)
    addition= models.JSONField(blank=True, null=True)
    image = CloudinaryField('image', blank=True, null=True)
    def __str__(self):
        return self.name

def generate_ticket_id():
    with transaction.atomic():
        last = Order.objects.select_for_update().order_by('-id').first()
        return (last.id + 1) if last else 100

class Order(models.Model):

    ORDER_TYPE_CHOICES = [
        ('Pending', 'Pending'),
        ('Ongoing', 'Ongoing'),
        ('Preparing', 'Preparing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS=[
        # ('InBucket', 'InBucket'),
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    id = models.IntegerField(primary_key=True , default=generate_ticket_id, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    items = models.ManyToManyField(Menu, through='OrderItem')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status =models.CharField(max_length=100, choices=ORDER_TYPE_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=100, choices=PAYMENT_STATUS, default='Unpaid')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def get_subtotal(self):
        return self.quantity * self.price

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)  # gpay / upi / razorpay / cash
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default="pending")  # pending / success / failed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.id} - {self.status}"


