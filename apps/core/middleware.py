from django.utils import timezone
from apps.accounts.models import AuditLog
import json

class AuditMiddleware:
    """Middleware to log all user activities"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log significant actions
        if request.user.is_authenticated and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=request.method,
                    model_name=request.path,
                    object_id='',
                    details={'path': request.path, 'method': request.method},
                    ip_address=self.get_client_ip(request)
                )
            except Exception:
                pass  # Don't break the request if logging fails
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class TimezoneMiddleware:
    """Middleware to handle user-specific timezones"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Set timezone based on user's company or preference
            # This would read from user profile
            timezone.activate('Africa/Harare')
        
        response = self.get_response(request)
        return response