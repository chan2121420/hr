from django.contrib import admin
from .models import LeaveType, Holiday, LeaveRequest

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_days_allocated', 'is_paid')

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date')

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 
        'leave_type', 
        'start_date', 
        'end_date', 
        'total_leave_days', 
        'status'
    )
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('employee__user__email', 'employee__user__first_name')
    readonly_fields = ('total_leave_days',)