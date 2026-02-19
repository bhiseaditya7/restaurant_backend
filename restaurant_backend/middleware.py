from django.utils.deprecation import MiddlewareMixin
from billing.models import Restaurant


class TenantMiddleware(MiddlewareMixin):

    def process_request(self, request):

        domain = None

        # 1️⃣ Try Origin header (most reliable for browsers)
        origin = request.headers.get("Origin")
        if origin:
            domain = origin.replace("https://", "").replace("http://", "").split("/")[0]

        # 2️⃣ Fallback Referer
        if not domain:
            referer = request.headers.get("Referer")
            if referer:
                domain = referer.replace("https://", "").replace("http://", "").split("/")[0]

        # 3️⃣ Fallback forwarded host
        if not domain:
            domain = request.headers.get("X-Forwarded-Host")

        # 4️⃣ Last fallback (direct API calls / postman)
        if not domain:
            domain = request.get_host()

        # 🛑 IMPORTANT: skip admin + api root domain
        if not domain or domain.startswith("api.") or domain.startswith("www.") or domain == "billfit.in":
            request.restaurant = None
            return

        # extract subdomain
        subdomain = domain.split(".")[0]

        try:
            request.restaurant = Restaurant.objects.get(subdomain=subdomain, is_active=True)
        except Restaurant.DoesNotExist:
            request.restaurant = None
