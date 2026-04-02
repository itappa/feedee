import ipaddress

from django.conf import settings


class AllowCIDRMiddleware:
    """Allow hosts matching ALLOWED_CIDR_NETS to bypass ALLOWED_HOSTS and CSRF checks."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.networks = [
            ipaddress.ip_network(cidr) for cidr in getattr(settings, "ALLOWED_CIDR_NETS", [])
        ]

    def __call__(self, request):
        host = request.META.get("HTTP_HOST", request.META.get("SERVER_NAME", ""))
        hostname = host.split(":")[0]
        try:
            ip = ipaddress.ip_address(hostname)
            if any(ip in net for net in self.networks):
                if hostname not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(hostname)
                origin = f"http://{host}"
                if origin not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(origin)
        except ValueError:
            pass
        return self.get_response(request)
