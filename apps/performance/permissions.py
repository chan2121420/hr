from rest_framework import permissions

class IsOwnerOrManagerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
            
        model_employee = obj.employee if hasattr(obj, 'employee') else obj
        
        if model_employee.manager == request.user.employee_profile:
            return True
            
        return model_employee == request.user.employee_profile