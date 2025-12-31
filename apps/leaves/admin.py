from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import LeaveType, Holiday, LeaveBalance, LeaveRequest, LeaveEncashment


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'default_days_allocated', 'is_paid',
        'color_badge', 'is_active'
    )
    list_filter = (
        'is_paid', 'is_active', 'requires_approval',
        'gender_specific', 'is_maternity_leave', 'is_paternity_leave'
    )
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'color_code', 'icon')
        }),
        ('Allocation', {
            'fields': (
                'default_days_allocated', 'max_days_allowed', 'min_days_allowed'
            )
        }),
        ('Properties', {
            'fields': (
                'is_paid', 'requires_approval', 'requires_manager_approval',
                'requires_hr_approval', 'requires_document'
            )
        }),
        ('Carryforward', {
            'fields': (
                'can_be_carried_forward', 'max_carry_forward_days',
                'carry_forward_expiry_months'
            )
        }),
        ('Accrual', {
            'fields': ('accrues_monthly', 'accrual_rate'),
            'classes': ('collapse',)
        }),
        ('Eligibility', {
            'fields': (
                'gender_specific', 'min_service_months', 'applies_to_probation',
                'notice_days_required'
            ),
            'classes': ('collapse',)
        }),
        ('Documentation', {
            'fields': (
                'medical_certificate_required',
                'medical_certificate_days_threshold'
            ),
            'classes': ('collapse',)
        }),
        ('Restrictions', {
            'fields': (
                'max_requests_per_year',
                'min_gap_days_between_requests'
            ),
            'classes': ('collapse',)
        }),
        ('Payroll Impact', {
            'fields': ('affects_salary', 'salary_deduction_percentage'),
            'classes': ('collapse',)
        }),
        ('Special Types', {
            'fields': (
                'is_emergency_leave', 'is_study_leave', 'is_compassionate_leave',
                'is_sabbatical', 'is_maternity_leave', 'is_paternity_leave'
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )
    
    def color_badge(self, obj):
        return format_html(
            '<div style="width: 50px; height: 25px; background: {}; border-radius: 5px;"></div>',
            obj.color_code
        )
    color_badge.short_description = 'Color'


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'date', 'is_recurring', 'is_national_holiday',
        'is_upcoming_display', 'falls_on_weekend'
    )
    list_filter = ('is_recurring', 'is_national_holiday', 'is_optional', 'date')
    search_fields = ('name', 'description')
    date_hierarchy = 'date'
    filter_horizontal = ('departments',)
    
    def is_upcoming_display(self, obj):
        if obj.is_upcoming:
            return format_html('<span style="color: #10B981;">✓ Upcoming</span>')
        return '-'
    is_upcoming_display.short_description = 'Upcoming'


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'leave_type', 'year', 'total_allocated',
        'used', 'pending', 'available_display', 'utilization_display'
    )
    list_filter = ('year', 'leave_type')
    search_fields = (
        'employee__user__first_name', 'employee__user__last_name',
        'employee__employee_id'
    )
    readonly_fields = ('available', 'utilization_percentage', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Employee & Type', {
            'fields': ('employee', 'leave_type', 'year')
        }),
        ('Balance', {
            'fields': (
                'total_allocated', 'used', 'pending',
                'available', 'utilization_percentage'
            )
        }),
        ('Carryforward', {
            'fields': ('carried_forward', 'carried_forward_expiry_date')
        }),
        ('Adjustments', {
            'fields': (
                'manual_adjustment', 'adjustment_reason',
                'adjusted_by', 'adjusted_at'
            ),
            'classes': ('collapse',)
        }),
        ('Accrual', {
            'fields': ('last_accrual_date', 'next_accrual_date'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['reset_balance', 'export_to_csv']
    
    def available_display(self, obj):
        available = obj.available
        color = '#10B981' if available > 5 else '#F59E0B' if available > 0 else '#EF4444'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f} days</span>',
            color, available
        )
    available_display.short_description = 'Available'
    
    def utilization_display(self, obj):
        pct = obj.utilization_percentage
        color = '#EF4444' if pct > 90 else '#F59E0B' if pct > 70 else '#10B981'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.0f}%</span>',
            color, pct
        )
    utilization_display.short_description = 'Utilization'
    
    def reset_balance(self, request, queryset):
        updated = queryset.update(used=0, pending=0, manual_adjustment=0)
        self.message_user(request, f'{updated} balance(s) reset.')
    reset_balance.short_description = 'Reset selected balances'


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'leave_type', 'start_date', 'end_date',
        'total_leave_days', 'status_badge', 'requested_at'
    )
    list_filter = (
        'status', 'leave_type', 'start_date', 'is_half_day',
        'is_urgent', 'is_emergency'
    )
    search_fields = (
        'employee__user__first_name', 'employee__user__last_name',
        'employee__employee_id', 'reason'
    )
    readonly_fields = (
        'total_leave_days', 'is_overlapping', 'days_until_start',
        'is_current', 'is_upcoming', 'requires_medical_certificate',
        'requested_at', 'updated_at'
    )
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Employee & Leave Type', {
            'fields': ('employee', 'leave_type')
        }),
        ('Dates', {
            'fields': (
                ('start_date', 'end_date'),
                'total_leave_days', 'is_overlapping', 'days_until_start',
                ('is_half_day', 'half_day_period')
            )
        }),
        ('Request Details', {
            'fields': (
                'reason', 'status', 'is_urgent', 'is_emergency',
                'requires_medical_certificate'
            )
        }),
        ('Documents', {
            'fields': ('supporting_document', 'additional_documents'),
            'classes': ('collapse',)
        }),
        ('Manager Approval', {
            'fields': (
                'manager_approved_by', 'manager_approved_at', 'manager_comments'
            ),
            'classes': ('collapse',)
        }),
        ('HR Approval', {
            'fields': (
                'hr_approved_by', 'hr_approved_at', 'hr_comments'
            ),
            'classes': ('collapse',)
        }),
        ('Rejection', {
            'fields': (
                'rejected_by', 'rejected_at', 'rejection_reason'
            ),
            'classes': ('collapse',)
        }),
        ('Handover', {
            'fields': (
                'handover_notes', 'covering_employee',
                'emergency_contact_name', 'emergency_contact_phone'
            ),
            'classes': ('collapse',)
        }),
        ('Return to Work', {
            'fields': (
                'actual_return_date', 'return_to_work_completed',
                'early_return', 'late_return', 'late_return_reason'
            ),
            'classes': ('collapse',)
        }),
        ('Status Info', {
            'fields': (
                'is_current', 'is_upcoming', 'requested_at', 'updated_at'
            )
        })
    )
    
    actions = ['approve_requests', 'reject_requests', 'export_to_csv']
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#F59E0B',
            'MANAGER_APPROVED': '#3B82F6',
            'HR_APPROVED': '#8B5CF6',
            'APPROVED': '#10B981',
            'REJECTED': '#EF4444',
            'CANCELLED': '#6B7280',
            'WITHDRAWN': '#9CA3AF',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def approve_requests(self, request, queryset):
        updated = 0
        for leave_request in queryset.filter(status='PENDING'):
            try:
                employee = request.user.employee_profile
                leave_request.approve_by_manager(employee, 'Bulk approved')
                updated += 1
            except:
                pass
        self.message_user(request, f'{updated} request(s) approved.')
    approve_requests.short_description = 'Approve selected requests'
    
    def reject_requests(self, request, queryset):
        updated = 0
        for leave_request in queryset.filter(status='PENDING'):
            leave_request.reject(request.user, 'Bulk rejected')
            updated += 1
        self.message_user(request, f'{updated} request(s) rejected.')
    reject_requests.short_description = 'Reject selected requests'


@admin.register(LeaveEncashment)
class LeaveEncashmentAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'leave_type', 'year', 'days_encashed',
        'total_amount', 'status_badge', 'requested_at'
    )
    list_filter = ('status', 'year', 'leave_type')
    search_fields = (
        'employee__user__first_name', 'employee__user__last_name',
        'employee__employee_id'
    )
    readonly_fields = ('total_amount', 'requested_at')
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#F59E0B',
            'APPROVED': '#10B981',
            'PROCESSED': '#3B82F6',
            'PAID': '#8B5CF6',
            'REJECTED': '#EF4444',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'