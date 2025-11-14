from rest_framework import permissions

class IsOwnerOrAssigneeOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        employee = request.user.employee_profile
        
        if hasattr(obj, 'assigned_to'):
            return obj.assigned_to == employee or obj.created_by == employee
            
        return False