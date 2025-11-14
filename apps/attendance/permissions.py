from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.employee.user == request.user

class IsEmployeeSelfOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        
        employee_id = view.kwargs.get('employee_pk')
        if not employee_id:
            return False
            
        return request.user.employee_profile.id == int(employee_id)