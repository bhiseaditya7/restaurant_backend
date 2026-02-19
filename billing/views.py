# users/views.py
import random



from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from datetime import timezone, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action, throttle_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, Throttled
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from django.db import transaction
from django.contrib.auth import authenticate

from django.core.cache import caches
from django.utils import timezone

from .models import User, Menu , Order, OrderItem
from .serializers import (
   
     AdminLoginSerializer,
     MenuSerializer,
     OrderStatusSerializer,
     RegisterUserSerializer,
     SignInSerializer, OrderSerializer
)
from drf_yasg.utils import swagger_auto_schema

from rest_framework import permissions

from rest_framework.permissions import AllowAny, IsAdminUser


# Patch for get_cache
cache = caches['default']


# User Logout Functionality
@method_decorator(csrf_exempt, name='dispatch')
class UserLogoutViewSet(APIView):
    permission_classes = [IsAuthenticated]
    '''blackout refresh token and clear session data'''

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception as e:
                return Response({"detail": f"Invalid or blacklisted token"}, status=status.HTTP_400_BAD_REQUEST)

            request.session.flush()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"Logout Failed: str(e)"}, status=status.HTTP_400_BAD_REQUEST)



class UserRegistration2(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterUserSerializer



class SignInView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = SignInSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)


class MenuViewSet(viewsets.ModelViewSet):
    # queryset = Menu.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = MenuSerializer

    def get_queryset(self):
        restaurant = self.request.restaurant
        if not restaurant:
            return Menu.objects.none()

        return Menu.objects.filter(restaurant=restaurant)

    def get_permissions(self):
        # Allow anyone to view menu
        if self.request.method in ['GET']:
            return [AllowAny()]
        
        # Only superuser/admin can modify menu
        return [IsAdminUser()]

# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer

# channel_layer = get_channel_layer()




class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]

    # def get_queryset(self):
    #     user = self.request.user

    #     # Prevent crash for Swagger / unauthenticated requests
    #     if not user.is_authenticated:
    #         return Order.objects.none()

    #     # Staff/Admin can see all orders
    #     if user.is_staff or user.is_superuser:
    #         return Order.objects.all().order_by("-id")

    #     # Normal users see only their own orders
    #     return Order.objects.filter(user=user).order_by("-created_at")

    # def get_queryset(self):
    #     restaurant = self.request.restaurant
    #     user = self.request.user

    #     if not restaurant:
    #         return Order.objects.none()

    #     qs = Order.objects.filter(restaurant=restaurant).exclude(status ='Pending')

    #     if not user.is_authenticated:
    #         return qs.none()

    #     if user.is_staff or user.is_superuser:
    #         return qs.order_by("-id")

    #     return qs.filter(user=user).exclude(status="Pending").order_by("-created_at")

    def get_queryset(self):
        restaurant = self.request.restaurant
        user = self.request.user

        if not restaurant:
            return Order.objects.none()

        # qs = (
        #     Order.objects.filter(restaurant=restaurant)
        #     .select_related("user", "restaurant")
        #     .prefetch_related("items__menu")
        # )
        qs = Order.objects.filter(restaurant=restaurant).select_related("user").prefetch_related("orderitem_set__menu")


        if not user.is_authenticated:
            return qs.none()

        if user.is_staff or user.is_superuser:
            return qs.order_by("-id")

        return qs.filter(user=user).exclude(status="Pending").order_by("-created_at")




    def perform_create(self, serializer):
        request = self.request

        payment_method = request.data.get("payment_method")

        # 🔥 STATUS DECISION
        if payment_method == "cash":
            status = "Ongoing"
        else:  # upi / card
            status = "Pending"

        serializer.save(
            user=request.user,
            restaurant=request.restaurant,
            status=status,
            payment_status="Unpaid"
        )

        # async_to_sync(channel_layer.group_send)(
        #     f"orders_{request.restaurant.subdomain}",
        #     {
        #         "type": "new_order",
        #         "data": {
        #             "event": "NEW_ORDER",
        #             "order_id": serializer.instance.id,
        #         }
        #     }
        # )



    def update(self, request, *args, **kwargs):
        raise PermissionDenied("Direct update not allowed")

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied("Direct update not allowed")


    @action(detail=True, methods=["put"], url_path="change-status")
    def change_status(self, request, pk=None):
        user = request.user

        if not (user.is_staff or user.is_superuser):
            raise PermissionDenied("Only admin can change order status")

        order = self.get_object()

        serializer = OrderStatusSerializer(
            order,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    

from .models import Payment
from .serializers import PaymentSerializer

class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        payment_method = request.data.get("payment_method")

        try:
            order = Order.objects.get(id=order_id, user=request.restaurant)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        # ✅ Always use backend-calculated total
        amount = order.total_price

        payment = Payment.objects.create(
            user=request.user,
            order=order,
            amount=amount,
            payment_method=payment_method,
            status="pending"
        )

        return Response({
            "payment_id": payment.id,
            "order_id": order.id,
            "amount": amount,
            "status": "created"
        })



class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")
        transaction_id = request.data.get("transaction_id")
        status_value = request.data.get("status")  # success / failed

        try:
            payment = Payment.objects.get(id=payment_id, user=request.user, order__restaurant = request.restaurant)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        if status_value == "success":
            payment.status = "success"
            payment.transaction_id = transaction_id
            payment.save()

            # Mark order paid
            payment.order.payment_status = "Paid"
            payment.order.status = "Ongoing"
            payment.order.save()

            return Response({"status": "success"})

        payment.status = "failed"
        payment.save()

        return Response({"status": "failed"})



# users/views.py
# users/views.py
# import razorpay
# from django.conf import settings

# client = razorpay.Client(
#     auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
# )


# class RazorpayCreatePayment(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         order_id = request.data.get("order_id")

#         order = Order.objects.get(id=order_id, user=request.user, restaurant = request.restaurant)
#         amount = int(order.total_price * 100)  # paise

#         client = razorpay.Client(
#             auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
#         )

#         razorpay_order = client.order.create({
#             "amount": amount,
#             "currency": "INR",
#             "payment_capture": 1
#         })

#         payment = Payment.objects.create(
#             user=request.user,
#             order=order,
#             amount=order.total_price,
#             payment_method="razorpay",
#             status="pending"
#         )

#         return Response({
#             "razorpay_key": settings.RAZORPAY_KEY_ID,
#             "razorpay_order_id": razorpay_order["id"],
#             "payment_id": payment.id,
#             "amount": amount
#         })
    

# from rest_framework.views import APIView
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from django.conf import settings
# import razorpay

# from .models import Order, Payment

# client = razorpay.Client(
#     auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
# )


# class VerifyRazorpayPayment(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         data = request.data

#         required_fields = [
#             "razorpay_order_id",
#             "razorpay_payment_id",
#             "razorpay_signature",
#             "payment_id",
#         ]

#         for field in required_fields:
#             if field not in data:
#                 return Response(
#                     {"error": f"{field} is required"},
#                     status=400
#                 )

#         try:
#             # 1️⃣ Verify Razorpay signature
#             client.utility.verify_payment_signature({
#                 "razorpay_order_id": data["razorpay_order_id"],
#                 "razorpay_payment_id": data["razorpay_payment_id"],
#                 "razorpay_signature": data["razorpay_signature"],
#             })

#             # 2️⃣ Fetch payment safely
#             payment = Payment.objects.select_related("order").get(
#                 id=data["payment_id"],
#                 user=request.user,
#                 order__restaurant = request.restaurant
#             )

#             if payment.status == "success":
#                 return Response({"status": "already_paid"})

#             # 3️⃣ Mark payment success
#             payment.status = "success"
#             payment.transaction_id = data["razorpay_payment_id"]
#             payment.save()

#             # 4️⃣ Update order
#             order = payment.order
#             order.payment_status = "Paid"
#             order.status = "Ongoing"
#             order.save()

#             return Response({
#                 "status": "success",
#                 "order_id": order.id
#             })

#         except Payment.DoesNotExist:
#             return Response(
#                 {"error": "Invalid payment"},
#                 status=404
#             )

#         except razorpay.errors.SignatureVerificationError:
#             return Response(
#                 {"status": "failed", "error": "Signature verification failed"},
#                 status=400
#             )



class AdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Order, Payment


# Single reusable client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


# ---------------------------
# CREATE PAYMENT ORDER
# ---------------------------
class RazorpayCreatePayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        restaurant = request.restaurant
        if not restaurant:
            return Response({"error": "Restaurant not detected"}, status=400)

        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"error": "order_id required"}, status=400)

        # Only allow own order of this restaurant
        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user,
            restaurant=restaurant
        )

        if order.payment_status == "Paid":
            return Response({"error": "Order already paid"}, status=400)

        amount = int(order.total_price * 100)  # paise

        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })

        # Create DB payment record (IMPORTANT: attach restaurant)
        payment = Payment.objects.create(
            user=request.user,
            order=order,
            restaurant=restaurant,
            amount=order.total_price,
            payment_method="razorpay",
            status="pending"
        )

        return Response({
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "payment_id": payment.id,
            "amount": amount
        })


class VerifyRazorpayPayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        restaurant = request.restaurant
        if not restaurant:
            return Response({"error": "Restaurant not detected"}, status=400)

        data = request.data

        required_fields = [
            "razorpay_order_id",
            "razorpay_payment_id",
            "razorpay_signature",
            "payment_id",
        ]

        for field in required_fields:
            if field not in data:
                return Response({"error": f"{field} is required"}, status=400)

        try:
            # 1️⃣ Verify Razorpay signature
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"],
            })

            # 2️⃣ Fetch payment securely (tenant safe)
            payment = Payment.objects.select_related("order").get(
                id=data["payment_id"],
                user=request.user,
                order__restaurant=restaurant
            )

            if payment.status == "success":
                return Response({"status": "already_paid"})

            # 3️⃣ Mark payment success
            payment.status = "success"
            payment.transaction_id = data["razorpay_payment_id"]
            payment.save()

            # 4️⃣ Update order
            order = payment.order
            order.payment_status = "Paid"
            order.status = "Ongoing"
            order.save()

            return Response({
                "status": "success",
                "order_id": order.id
            })

        except Payment.DoesNotExist:
            return Response({"error": "Invalid payment"}, status=404)

        except razorpay.errors.SignatureVerificationError:
            return Response(
                {"status": "failed", "error": "Signature verification failed"},
                status=400
            )
