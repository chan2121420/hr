from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Shift, AttendanceRecord, AttendanceBreak, AttendanceException,
    AttendancePolicy, AttendanceSummary, PublicHoliday
)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'time_range', 'expected_hours',
        'employee_count_display', 'color_badge', 'is_active'
    )
    list_filter = ('is_active', 'shift_type', 'has_paid_break')
    search_fields = ('name', 'code')
    readonly_fields = ('expected_hours', 'is_night_shift', 'working_days_count')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'shift_type', 'color_code')
        }),
        ('Timing', {
            'fields': (
                ('start_time', 'end_time'),
                'expected_hours', 'is_night_shift',
                ('break_duration_minutes', 'has_paid_break')
            )
        }),
        ('Grace Periods', {
            'fields': (
                'grace_period_minutes',
                'early_departure_grace_minutes'
            )
        }),
        ('Working Days', {
            'fields': (
                ('monday', 'tuesday', 'wednesday', 'thursday'),
                ('friday', 'saturday', 'sunday'),
                'working_days_count'
            )
        }),
        ('Overtime Settings', {
            'fields': (
                'overtime_threshold_minutes',
                'overtime_multiplier'
            )
        }),
        ('Geofencing', {
            'fields': (
                'requires_geofencing',
                'geofence_radius_meters',
                'allowed_locations'
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def time_range(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
    time_range.short_description = 'Time Range'
    
    def employee_count_display(self, obj):
        count = obj.employees.filter(status='ACTIVE').count()
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            obj.color_code, count
        )
    employee_count_display.short_description = 'Employees'
    
    def color_badge(self, obj):
        return format_html(
            '<div style="width: 50px; height: 25px; background: {}; border-radius: 5px;"></div>',
            obj.color_code
        )
    color_badge.short_description = 'Color'


class AttendanceBreakInline(admin.TabularInline):
    model = AttendanceBreak
    extra = 0
    fields = ('break_type', 'break_start', 'break_end', 'duration_minutes')
    readonly_fields = ('duration_minutes',)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        'employee_info', 'date', 'status_badge', 'shift',
        'clock_times', 'work_hours_display', 'overtime_display',
        'verification_status'
    )
    list_filter = (
        'date', 'status', 'shift', 'is_late', 'is_verified',
        'is_remote', 'is_weekend_work', 'is_public_holiday_work'
    )
    search_fields = (
        'employee__user__first_name', 'employee__user__last_name',
        'employee__employee_id'
    )
    readonly_fields = (
        'work_hours', 'overtime_hours', 'punctuality_score',
        'efficiency_score', 'overtime_pay_multiplier'
    )
    date_hierarchy = 'date'
    inlines = [AttendanceBreakInline]
    
    fieldsets = (
        ('Employee & Date', {
            'fields': ('employee', 'date', 'shift', 'status')
        }),
        ('Clock Times', {
            'fields': (
                ('clock_in', 'clock_out'),
                ('is_late', 'late_minutes'),
                ('is_early_departure', 'early_departure_minutes')
            )
        }),
        ('Work Details', {
            'fields': (
                'work_hours', 'overtime_hours', 'overtime_pay_multiplier',
                'total_break_minutes', 'punctuality_score', 'efficiency_score',
                ('productive_hours', 'tasks_completed'),
                'work_summary', 'work_quality_rating'
            )
        }),
        ('Location Tracking', {
            'fields': (
                ('clock_in_location', 'clock_out_location'),
                ('clock_in_latitude', 'clock_in_longitude'),
                ('clock_out_latitude', 'clock_out_longitude'),
                ('is_outside_geofence', 'geofence_violation_distance')
            ),
            'classes': ('collapse',)
        }),
        ('Device & IP', {
            'fields': (
                ('clock_in_ip', 'clock_out_ip'),
                ('clock_in_device', 'clock_out_device'),
            ),
            'classes': ('collapse',)
        }),
        ('Photos', {
            'fields': ('clock_in_photo', 'clock_out_photo'),
            'classes': ('collapse',)
        }),
        ('Flags', {
            'fields': (
                'is_remote', 'is_weekend_work', 'is_public_holiday_work',
                'is_manually_entered'
            )
        }),
        ('Verification', {
            'fields': (
                ('requires_verification', 'is_verified'),
                ('approved_by', 'approved_at')
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        })
    )
    
    actions = ['mark_as_verified', 'mark_as_present', 'export_to_csv']
    
    def employee_info(self, obj):
        url = reverse('admin:employees_employee_change', args=[obj.employee.id])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url, obj.employee.full_name, obj.employee.employee_id
        )
    employee_info.short_description = 'Employee'
    
    def status_badge(self, obj):
        colors = {
            'PRESENT': '#10B981',
            'LATE': '#F59E0B',
            'ABSENT': '#EF4444',
            'ON_LEAVE': '#3B82F6',
            'OVERTIME': '#8B5CF6',
            'PENDING': '#6B7280',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def clock_times(self, obj):
        if obj.clock_in and obj.clock_out:
            return format_html(
                '{}<br><small>to</small><br>{}',
                obj.clock_in.strftime('%H:%M'),
                obj.clock_out.strftime('%H:%M')
            )
        elif obj.clock_in:
            return format_html('{}<br><small>Not clocked out</small>', obj.clock_in.strftime('%H:%M'))
        return '-'
    clock_times.short_description = 'Clock Times'
    
    def work_hours_display(self, obj):
        hours = obj.work_hours
        if hours > 0:
            return format_html('<strong>{:.2f}</strong> hrs', hours)
        return '-'
    work_hours_display.short_description = 'Work Hours'
    
    def overtime_display(self, obj):
        ot = obj.overtime_hours
        if ot > 0:
            return format_html(
                '<span style="color: #F59E0B; font-weight: bold;">{:.2f} hrs</span>',
                ot
            )
        return '-'
    overtime_display.short_description = 'Overtime'
    
    def verification_status(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: #10B981;">✓ Verified</span>')
        elif obj.requires_verification:
            return format_html('<span style="color: #F59E0B;">⚠ Pending</span>')
        return '-'
    verification_status.short_description = 'Verification'
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} records marked as verified.')
    mark_as_verified.short_description = 'Mark as verified'
    
    def mark_as_present(self, request, queryset):
        updated = queryset.update(status='PRESENT')
        self.message_user(request, f'{updated} records marked as present.')
    mark_as_present.short_description = 'Mark as present'


@admin.register(AttendanceException)
class AttendanceExceptionAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'exception_date', 'exception_type',
        'status_badge', 'is_urgent', 'created_at'
    )
    list_filter = ('status', 'exception_type', 'is_urgent', 'exception_date')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'reason')
    readonly_fields = ('reviewed_by', 'reviewed_at')
    
    fieldsets = (
        ('Exception Details', {
            'fields': (
                'employee', 'exception_date', 'exception_type',
                'reason', 'supporting_document', 'is_urgent'
            )
        }),
        ('Proposed Corrections', {
            'fields': (
                'proposed_clock_in', 'proposed_clock_out', 'proposed_status'
            )
        }),
        ('Review', {
            'fields': (
                'status', 'reviewed_by', 'reviewed_at', 'review_comments'
            )
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#F59E0B',
            'APPROVED': '#10B981',
            'REJECTED': '#EF4444',
            'CANCELLED': '#6B7280',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'month_year', 'attendance_percentage_display',
        'punctuality_score_display', 'total_work_hours', 'generated_at'
    )
    list_filter = ('year', 'month', 'has_disciplinary_issues')
    search_fields = ('employee__user__first_name', 'employee__user__last_name')
    readonly_fields = (
        'absence_rate', 'overall_score', 'attendance_percentage',
        'punctuality_score', 'generated_at'
    )
    
    def month_year(self, obj):
        return f"{obj.month}/{obj.year}"
    month_year.short_description = 'Period'
    
    def attendance_percentage_display(self, obj):
        pct = obj.attendance_percentage
        color = '#10B981' if pct >= 90 else '#F59E0B' if pct >= 75 else '#EF4444'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, pct
        )
    attendance_percentage_display.short_description = 'Attendance'
    
    def punctuality_score_display(self, obj):
        score = obj.punctuality_score
        color = '#10B981' if score >= 90 else '#F59E0B' if score >= 75 else '#EF4444'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, score
        )
    punctuality_score_display.short_description = 'Punctuality'


@admin.register(AttendancePolicy)
class AttendancePolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'effective_from', 'effective_to', 'is_active', 'is_currently_effective')
    list_filter = ('is_active', 'effective_from')
    readonly_fields = ('is_currently_effective',)


@admin.register(PublicHoliday)
class PublicHolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'is_recurring', 'is_paid', 'pay_multiplier')
    list_filter = ('is_recurring', 'is_paid', 'date')
    search_fields = ('name',)
    ordering = ['-date']

