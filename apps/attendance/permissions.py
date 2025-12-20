from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow owners or admins to access"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        try:
            return obj.employee.user == request.user
        except:
            return False


class CanManageAttendance(permissions.BasePermission):
    """Allow managers and admins to manage attendance"""
    
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        
        try:
            employee = request.user.employee_profile
            return employee.can_approve_timesheets or employee.is_manager
        except:
            return False


class CanApproveAttendance(permissions.BasePermission):
    """Allow only users with approval permissions"""
    
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        
        try:
            employee = request.user.employee_profile
            return employee.can_approve_timesheets
        except:
            return False
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        try:
            employee = request.user.employee_profile
            # Can approve if they're the employee's manager
            return obj.employee.manager == employee
        except:
            return False