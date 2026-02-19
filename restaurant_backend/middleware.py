# from django.utils.deprecation import MiddlewareMixin
# from billing.models import Restaurant


# class TenantMiddleware(MiddlewareMixin):

#     def process_request(self, request):

#         domain = None

#         # 1️⃣ Try Origin header (most reliable for browsers)
#         origin = request.headers.get("Origin")
#         if origin:
#             domain = origin.replace("https://", "").replace("http://", "").split("/")[0]

#         # 2️⃣ Fallback Referer
#         if not domain:
#             referer = request.headers.get("Referer")
#             if referer:
#                 domain = referer.replace("https://", "").replace("http://", "").split("/")[0]

#         # 3️⃣ Fallback forwarded host
#         if not domain:
#             domain = request.headers.get("X-Forwarded-Host")

#         # 4️⃣ Last fallback (direct API calls / postman)
#         if not domain:
#             domain = request.get_host()

#         # 🛑 IMPORTANT: skip admin + api root domain
#         if not domain or domain.startswith("api.") or domain.startswith("www.") or domain == "billfit.in":
#             request.restaurant = None
#             return

#         # extract subdomain
#         subdomain = domain.split(".")[0]

#         try:
#             request.restaurant = Restaurant.objects.get(subdomain=subdomain, is_active=True)
#         except Restaurant.DoesNotExist:
#             request.restaurant = None


# from django.utils.deprecation import MiddlewareMixin
# from billing.models import Restaurant


# class TenantMiddleware(MiddlewareMixin):
#     """
#     Resolves restaurant based on subdomain.

#     Works for:
#     - production:  saishwar.billfit.in
#     - local:       saishwar.127.0.0.1.nip.io
#     - staging:     saishwar.staging.billfit.in
#     """

#     ROOT_DOMAINS = [
#         "billfit.in",
#         "localhost",
#         "127.0.0.1",
#         "nip.io",
#         "sslip.io",
#     ]

#     RESERVED_SUBDOMAINS = [
#         "www",
#         "api",
#         "admin",
#     ]

#     def get_domain(self, request):
#         """
#         Get real host safely behind proxy / cloudflare / nginx
#         """
#         # Cloudflare / proxy header (highest priority)
#         forwarded = request.headers.get("X-Forwarded-Host")
#         if forwarded:
#             return forwarded.split(",")[0].split(":")[0].lower()

#         # Normal host
#         return request.get_host().split(":")[0].lower()

#     def extract_subdomain(self, host):
#         """
#         Extract subdomain from any supported domain
#         """

#         parts = host.split(".")

#         # Examples:
#         # saishwar.billfit.in -> ['saishwar','billfit','in']
#         # saishwar.127.0.0.1.nip.io -> ['saishwar','127','0','0','1','nip','io']

#         if len(parts) < 3:
#             return None

#         subdomain = parts[0]

#         if subdomain in self.RESERVED_SUBDOMAINS:
#             return None

#         return subdomain

#     def process_request(self, request):

#         host = self.get_domain(request)

#         # Root domains should not map to tenant
#         if any(host == root or host.endswith("." + root) and host.count(".") == root.count(".")
#                for root in self.ROOT_DOMAINS):
#             request.restaurant = None
#             return
        
#         print("HOST:", request.get_host())
#         print("ORIGIN:", request.headers.get("Origin"))
#         print("REFERER:", request.headers.get("Referer"))
#         print("RESOLVED DOMAIN:", domain)
#         print("SUBDOMAIN:", domain.split(".")[0] if domain else None)
#         print("RESTAURANT FOUND:", request.restaurant)
#         print("-----")


#         subdomain = self.extract_subdomain(host)

#         if not subdomain:
#             request.restaurant = None
#             return

#         try:
#             request.restaurant = Restaurant.objects.get(
#                 subdomain=subdomain,
#                 is_active=True
#             )
#         except Restaurant.DoesNotExist:
#             request.restaurant = None


# from django.utils.deprecation import MiddlewareMixin
# from billing.models import Restaurant


# class TenantMiddleware(MiddlewareMixin):

#     def process_request(self, request):

#         request.restaurant = None
#         domain = None

#         # 1️⃣ MOST RELIABLE (browser navigation)
#         referer = request.headers.get("Referer")
#         if referer:
#             domain = referer.split("://")[-1].split("/")[0]

#         # 2️⃣ API calls (fetch/axios)
#         if not domain:
#             origin = request.headers.get("Origin")
#             if origin:
#                 domain = origin.split("://")[-1].split("/")[0]

#         # 3️⃣ Direct calls / Postman
#         if not domain:
#             domain = request.get_host()

#         if not domain:
#             return

#         # remove port
#         domain = domain.split(":")[0]

#         # ignore platform domains
#         if (
#             domain == "billfit.in"
#             or domain == "www.billfit.in"
#             or domain.startswith("api.")
#         ):
#             return

#         # extract subdomain safely
#         subdomain = domain.split(".")[0]

#         try:
#             request.restaurant = Restaurant.objects.get(
#                 subdomain=subdomain,
#                 is_active=True
#             )
#         except Restaurant.DoesNotExist:
#             request.restaurant = None


from django.utils.deprecation import MiddlewareMixin
from billing.models import Restaurant
from django.core.cache import cache


class TenantMiddleware(MiddlewareMixin):

    def process_request(self, request):

        request.restaurant = None
        domain = None

        # 1️⃣ MOST RELIABLE (browser navigation)
        referer = request.headers.get("Referer")
        if referer:
            domain = referer.split("://")[-1].split("/")[0]

        # 2️⃣ API calls (fetch/axios)
        if not domain:
            origin = request.headers.get("Origin")
            if origin:
                domain = origin.split("://")[-1].split("/")[0]

        # 3️⃣ Direct calls / Postman
        if not domain:
            domain = request.get_host()

        if not domain:
            return

        # remove port
        domain = domain.split(":")[0]

        # ignore platform domains
        if (
            domain == "billfit.in"
            or domain == "www.billfit.in"
            or domain.startswith("api.")
        ):
            return

        # extract subdomain safely
        subdomain = domain.split(".")[0]

        # 🚀 CACHE OPTIMIZATION
        cache_key = f"tenant_restaurant_{subdomain}"
        restaurant = cache.get(cache_key)

        if restaurant is None:
            try:
                restaurant = Restaurant.objects.get(
                    subdomain=subdomain,
                    is_active=True
                )
                cache.set(cache_key, restaurant, 300)
            except Restaurant.DoesNotExist:
                restaurant = None

        request.restaurant = restaurant
