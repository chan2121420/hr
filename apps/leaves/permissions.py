
from rest_framework.permissions import BasePermission



class IsOwnerOrManagerOrAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):

        user = request.user

        if user.is_staff:

            return True

        employee = user.employee_profile

        return obj.employee == employee or obj.employee.manager == employee



class IsManagerOrAdmin(BasePermission):

    def has_permission(self, request, view):

        user = request.user

        return user.is_staff or hasattr(user, 'employee_profile') and user.employee_profile.is_manager

