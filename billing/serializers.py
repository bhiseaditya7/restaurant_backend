# users/serializers.py
import logging
import random
from datetime import timedelta
from datetime import datetime
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password

from django.core.validators import RegexValidator
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


from axes.models import AccessAttempt
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate

from .models import Menu, Order, OrderItem
FAILURE_LIMIT = 5
COOLOFF_TIME = timedelta(minutes=1)
# logging.getLogger("django.utils.autoreload").setLevel(logging.WARNING)
# logger = logging.getLogger('custom_logger')
# OTP Constants
OTP_LENGTH = 6
OTP_EXPIRY_TIME = 600  # 10 minutes


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class TokenSerializer(serializers.Serializer):
    """Serializer for generating JWT tokens"""
    @staticmethod
    def get_token(user):
        refresh = RefreshToken.for_user(user)
        return{
            'refresh': str(refresh),
            'access': str(refresh.token)
        }





class RegisterUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'phone_number', 'email']



class SignInSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate(self, data):
        phone_number = data.get("phone_number")

        # Step 1: Check if user exists
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found. Please register.")

        # Step 2: Check active status
        if not user.is_active:
            raise AuthenticationFailed("Account is disabled")

        # Step 3: Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Step 4: Return user data + tokens
        return {
            "user_id": user.id,
            "name": user.name,
            "phone_number": user.phone_number,
            "email": user.email,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }
    

class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = ['id', 'name', 'description', 'price', 'is_vegetarian', 'rating', 'addition', 'image']


class OrderItemSerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source="menu.name", read_only=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['menu', 'menu_name', 'quantity', 'price']

    def validate_menu(self, menu):
        request = self.context["request"]
        restaurant = request.restaurant

        if menu.restaurant_id != restaurant.id:
            raise serializers.ValidationError("This menu does not belong to this restaurant")

        return menu


class OrderUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "phone_number"]  

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source="orderitem_set", many=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_details = OrderUserSerializer(source="user", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "user_details",
            "items",
            "total_price",
            "status",
            "payment_status",
            "created_at"
        ]
        read_only_fields = ["id", "user_details","total_price", "status",  "payment_status","created_at"]

    # def create(self, validated_data):
    #     items_data = validated_data.pop("orderitem_set", [])

    #     # Create empty order first
    #     order = Order.objects.create(total_price=0, **validated_data)

    #     total = 0

    #     for item in items_data:
    #         menu = item["menu"]
    #         quantity = item.get("quantity", 1)

    #         price = menu.price  # ✅ price comes from DB only

    #         OrderItem.objects.create(
    #             order=order,
    #             menu=menu,
    #             quantity=quantity,
    #             price=price
    #         )

    #         total += price * quantity

    #     order.total_price = total
    #     order.save()

    #     return order

    def create(self, validated_data):
        request = self.context["request"]
        restaurant = request.restaurant

        if not restaurant:
            raise serializers.ValidationError("Restaurant not detected")

        items_data = validated_data.pop("orderitem_set", [])

        # attach restaurant automatically
        order = Order.objects.create(
            restaurant=restaurant,
            user=request.user,
            total_price=0,
            **validated_data
        )

        total = 0

        for item in items_data:
            menu = item["menu"]
            quantity = item.get("quantity", 1)

            # 🔒 SECURITY: menu must belong to same restaurant
            if menu.restaurant_id != restaurant.id:
                raise serializers.ValidationError(
                    f"{menu.name} does not belong to this restaurant"
                )

            price = menu.price

            OrderItem.objects.create(
                order=order,
                menu=menu,
                quantity=quantity,
                price=price
            )

            total += price * quantity

        order.total_price = total
        order.save()

        return order

    
class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status", "payment_status"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user
        order = self.instance

        
        if order.restaurant_id != request.restaurant.id:
            raise serializers.ValidationError("Cannot modify another restaurant order")

        if not (user.is_staff or user.is_superuser):
            raise serializers.ValidationError(
                "Only admin can update order status or payment"
            )

        # Allowed transitions
        allowed_statuses = ["Ongoing", "Preparing", "Completed", "Cancelled"]

        if "status" in attrs:
            if attrs["status"] not in allowed_statuses:
                raise serializers.ValidationError(
                    f"Invalid status: {attrs['status']}"
                )

        if "payment_status" in attrs:
            if attrs["payment_status"] != "Paid":
                raise serializers.ValidationError(
                    "Admin can only mark payment as Paid"
                )

        return attrs


from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    # class Meta:
    #     model = Payment
    #     fields = "__all__"
    class Meta:
        model = Payment
        fields = ["id", "order", "amount", "payment_method", "status", "created_at"]
        read_only_fields = ["status"]



class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    print("pp",password)
    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"].strip()

        print(f"Admin login attempt: {email}")
        print(f"Password provided: {'Yes' if password else 'No'}")
        print("password type:", password)
        user = User.objects.filter(email=email).first()

        print("USER FOUND:", user)
        if user:
            print("DB PASSWORD:", user.password)
            print("CHECK PASSWORD:", user.check_password(password))
            print("IS STAFF:", user.is_staff)
            print("IS SUPERUSER:", user.is_superuser)

        print("RAW PASSWORD REPR:", repr(password))
        print("CHECK 1:", user.check_password(password))

        pwd = password.strip()
        print("CHECK STRIPPED:", user.check_password(pwd))


        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password")

        if not (user.is_staff or user.is_superuser):
            raise serializers.ValidationError("Not authorized as admin")

        refresh = RefreshToken.for_user(user)

        return {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": True,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }
