from rest_framework import permissions

class IsHRManager(permissions.BasePermission):
    """Allow only HR managers"""
    def has_permission(self, request, view):
        return request.user.role in ['hr_manager', 'admin']

class IsManagerOrOwner(permissions.BasePermission):
    """Allow managers or object owner"""
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['admin', 'hr_manager']:
            return True
        if hasattr(obj, 'employee'):
            return obj.employee == request.user.employee
        return False

class CanApproveLeave(permissions.BasePermission):
    """Check if user can approve leave"""
    def has_permission(self, request, view):
        return request.user.has_perm('accounts.approve_leave')