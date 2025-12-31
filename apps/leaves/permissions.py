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


class CanApproveLeave(BasePermission):
    """
    Permission to approve leave requests
    - Manager can approve their team's requests
    - HR can approve requests requiring HR approval
    - Admin can approve any request
    """
    
    def has_permission(self, request, view):
        """Check if user can approve leaves"""
        user = request.user
        
        if not user or not user.is_authenticated:
            return False
        
        # Admin/staff can approve
        if user.is_staff or user.is_superuser:
            return True
        
        # Check if user is manager or HR
        try:
            employee = user.employee_profile
            is_manager = employee.is_manager or employee.subordinates.exists()
            is_hr = user.groups.filter(name__in=['HR', 'HR Manager', 'HR Admin']).exists()
            return is_manager or is_hr
        except AttributeError:
            # Check if user is HR even without employee profile
            return user.groups.filter(name__in=['HR', 'HR Manager', 'HR Admin']).exists()
    
    def has_object_permission(self, request, view, obj):
        """Check if user can approve this specific leave request"""
        user = request.user
        
        # Admin can approve anything
        if user.is_staff or user.is_superuser:
            return True
        
        try:
            employee = user.employee_profile
            
            # Manager can approve their team's requests
            if obj.employee.manager == employee:
                # Can approve if status is PENDING
                if obj.status == 'PENDING':
                    return True
                # HR users can approve MANAGER_APPROVED requests
                if obj.status == 'MANAGER_APPROVED':
                    return user.groups.filter(name__in=['HR', 'HR Manager', 'HR Admin']).exists()
            
            # HR can approve requests requiring HR approval
            if obj.leave_type.requires_hr_approval:
                is_hr = user.groups.filter(name__in=['HR', 'HR Manager', 'HR Admin']).exists()
                if is_hr and obj.status == 'MANAGER_APPROVED':
                    return True
            
        except AttributeError:
            # User without employee profile but in HR group
            if user.groups.filter(name__in=['HR', 'HR Manager', 'HR Admin']).exists():
                if obj.status == 'MANAGER_APPROVED' and obj.leave_type.requires_hr_approval:
                    return True
        
        return False