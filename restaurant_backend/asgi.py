# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import billing.routing

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_backend.settings')

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             billing.routing.websocket_urlpatterns
#         )
#     ),
# })



import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_backend.settings')

application = get_asgi_application()