#users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
  
    MenuViewSet, OrderViewSet, SignInView, UserLogoutViewSet,   UserRegistration2, CreatePaymentView, VerifyPaymentView , RazorpayCreatePayment, VerifyRazorpayPayment
)

app_name = 'billing'

router = DefaultRouter()
# router.register('profile', UserProfileViewSet, basename='user-profile')

router.register('register2', UserRegistration2, basename='regitratiopn')
router.register('menu', MenuViewSet, basename='menu')
router.register('orders', OrderViewSet, basename='orders')


urlpatterns = [
    path('', include(router.urls)),
   
    path('login/', SignInView.as_view(), name='user_login'),
    path('logout/', UserLogoutViewSet.as_view(), name='user_logout'),
    path("payments/create/", CreatePaymentView.as_view()),
    path("payments/verify/", VerifyPaymentView.as_view()),
    path("payments/razorpay/create/", RazorpayCreatePayment.as_view()),
    path("payments/razorpay/verify/", VerifyRazorpayPayment.as_view()),
]
