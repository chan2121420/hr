from django.contrib import admin
from .models import Shift, AttendanceRecord

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time', 'expected_hours')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 
        'date', 
        'status', 
        'clock_in', 
        'clock_out', 
        'work_hours',
        'overtime_hours'
    )
    list_filter = ('date', 'status', 'shift')
    search_fields = ('employee__user__email', 'employee__user__first_name')
    list_editable = ('status', 'clock_in', 'clock_out')
    readonly_fields = ('work_hours', 'overtime_hours')