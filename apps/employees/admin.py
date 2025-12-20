from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Department, Designation, Employee, EmergencyContact,
    BankDetails, EmployeeDocument, Dependent, EmployeeNote
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'head', 'employee_count_display',
        'budget_utilization', 'is_active'
    )
    list_filter = ('is_active', 'location', 'parent_department')
    search_fields = ['name', 'code', 'email']
    readonly_fields = ('created_at', 'updated_at', 'budget_utilization_display')
    autocomplete_fields = ['head', 'parent_department']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'head', 'parent_department')
        }),
        ('Budget', {
            'fields': ('annual_budget', 'budget_used', 'budget_utilization_display', 'cost_center_code')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'location')
        }),
        ('Goals & Objectives', {
            'fields': ('objectives', 'kpis'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def employee_count_display(self, obj):
        count = obj.employee_count
        return format_html(
            '<span style="background: #10B981; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            count
        )
    employee_count_display.short_description = 'Employees'
    
    def budget_utilization(self, obj):
        percentage = obj.budget_utilization_percentage
        if percentage > 90:
            color = '#EF4444'
        elif percentage > 75:
            color = '#F59E0B'
        else:
            color = '#10B981'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, percentage
        )
    budget_utilization.short_description = 'Budget Used'
    
    def budget_utilization_display(self, obj):
        if obj.annual_budget:
            return f"{obj.budget_utilization_percentage:.1f}% (${obj.budget_used:,.2f} / ${obj.annual_budget:,.2f})"
        return 'N/A'
    budget_utilization_display.short_description = 'Budget Utilization'


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'code', 'level', 'salary_range_display',
        'employee_count_display', 'is_active'
    )
    list_filter = ('level', 'is_active', 'eligible_for_bonus')
    search_fields = ['title', 'code']
    readonly_fields = ('created_at', 'updated_at', 'current_employee_count')
    autocomplete_fields = ['reports_to', 'next_level_designation']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'code', 'description', 'level')
        }),
        ('Salary Range', {
            'fields': ('min_salary', 'max_salary')
        }),
        ('Reporting Structure', {
            'fields': ('reports_to', 'next_level_designation')
        }),
        ('Requirements', {
            'fields': (
                'required_education', 'required_experience_years',
                'required_skills', 'required_certifications',
                'key_responsibilities'
            ),
            'classes': ('collapse',)
        }),
        ('Benefits', {
            'fields': (
                'eligible_for_bonus', 'eligible_for_overtime',
                'eligible_for_company_car'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'current_employee_count', 'created_at', 'updated_at')
        }),
    )
    
    def employee_count_display(self, obj):
        count = obj.current_employee_count
        return format_html(
            '<span style="background: #667eea; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            count
        )
    employee_count_display.short_description = 'Employees'


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1
    fields = ('name', 'relationship', 'phone_number', 'is_primary', 'can_make_medical_decisions')


class BankDetailsInline(admin.StackedInline):
    model = BankDetails
    can_delete = False
    fields = (
        ('bank_name', 'account_type'),
        ('account_number', 'account_holder_name'),
        ('branch_name', 'branch_code'),
        ('has_mobile_money', 'mobile_money_provider', 'mobile_money_number'),
        ('is_verified', 'verified_at', 'verified_by')
    )
    readonly_fields = ('is_verified', 'verified_at', 'verified_by')


class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 0
    fields = ('document_type', 'title', 'document', 'is_verified', 'expiry_date')
    readonly_fields = ('is_verified',)


class DependentInline(admin.TabularInline):
    model = Dependent
    extra = 0
    fields = ('name', 'relationship', 'date_of_birth', 'is_on_medical_aid', 'is_tax_dependent')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id', 'full_name_display', 'department',
        'designation', 'manager', 'status_badge', 'tenure_display',
        'join_date'
    )
    list_filter = (
        'status', 'employment_type', 'department', 'designation',
        'work_location', 'is_remote_worker', 'join_date'
    )
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'employee_id', 'national_id', 'work_email'
    ]
    autocomplete_fields = ['user', 'manager', 'department', 'designation']
    readonly_fields = (
        'employee_id', 'created_at', 'updated_at', 'tenure_display',
        'is_on_probation', 'probation_days_remaining', 'subordinate_count',
        'is_manager'
    )
    
    date_hierarchy = 'join_date'
    
    inlines = [BankDetailsInline, EmergencyContactInline, DependentInline, EmployeeDocumentInline]
    
    fieldsets = (
        ('User Account', {
            'fields': ('user', 'employee_id')
        }),
        ('Employment Details', {
            'fields': (
                ('department', 'designation', 'manager'),
                ('status', 'employment_type'),
                ('join_date', 'probation_end_date', 'confirmation_date'),
                'is_on_probation', 'probation_days_remaining'
            )
        }),
        ('Contact Information', {
            'fields': (
                ('work_email', 'work_phone'),
                ('work_location', 'office_location')
            )
        }),
        ('Zimbabwe-Specific', {
            'fields': (
                ('national_id', 'tax_number'),
                ('nssa_number', 'pension_number')
            )
        }),
        ('Contract Details', {
            'fields': (
                ('contract_type', 'contract_start_date', 'contract_end_date')
            ),
            'classes': ('collapse',)
        }),
        ('Compensation', {
            'fields': (
                ('current_salary', 'salary_currency')
            )
        }),
        ('Performance', {
            'fields': (
                ('performance_rating', 'last_review_date', 'next_review_date')
            )
        }),
        ('Skills & Competencies', {
            'fields': ('skills', 'certifications', 'languages'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': (
                'can_approve_expenses', 'can_recruit',
                'can_approve_leave', 'can_approve_timesheets'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Flags', {
            'fields': (
                'is_remote_worker', 'is_union_member',
                'has_security_clearance'
            ),
            'classes': ('collapse',)
        }),
        ('Management Info', {
            'fields': ('is_manager', 'subordinate_count'),
            'classes': ('collapse',)
        }),
        ('Termination Details', {
            'fields': (
                ('termination_date', 'termination_type'),
                'termination_reason',
                ('eligible_for_rehire', 'exit_interview_completed'),
                ('exit_interview_date', 'final_settlement_date')
            ),
            'classes': ('collapse',)
        }),
        ('Onboarding', {
            'fields': ('onboarding_completed', 'onboarding_completion_date'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'tenure_display')
        }),
    )
    
    actions = ['confirm_probation', 'mark_as_active', 'export_to_csv']
    
    def full_name_display(self, obj):
        avatar_url = f"https://ui-avatars.com/api/?name={obj.user.first_name}+{obj.user.last_name}&size=30&background=667eea&color=fff"
        return format_html(
            '<img src="{}" style="border-radius: 50%; margin-right: 10px;" /> {}',
            avatar_url,
            obj.full_name
        )
    full_name_display.short_description = 'Name'
    
    def status_badge(self, obj):
        colors = {
            'ACTIVE': '#10B981',
            'PROBATION': '#F59E0B',
            'ON_LEAVE': '#3B82F6',
            'SUSPENDED': '#EF4444',
            'TERMINATED': '#6B7280',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 10px; border-radius: 5px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def tenure_display(self, obj):
        years = obj.tenure_years
        if years >= 1:
            return f"{years} years"
        else:
            months = obj.tenure_months
            return f"{months} months"
    tenure_display.short_description = 'Tenure'
    
    def confirm_probation(self, request, queryset):
        from datetime import date
        updated = 0
        for employee in queryset.filter(status='PROBATION'):
            employee.status = 'ACTIVE'
            employee.confirmation_date = date.today()
            employee.save()
            updated += 1
        self.message_user(request, f"{updated} employee(s) confirmed successfully.")
    confirm_probation.short_description = "Confirm selected employees"
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f"{updated} employee(s) marked as active.")
    mark_as_active.short_description = "Mark selected as active"

    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="employees.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Name', 'Email', 'Department',
            'Designation', 'Status', 'Join Date'
        ])
        
        for emp in queryset:
            writer.writerow([
                emp.employee_id,
                emp.full_name,
                emp.work_email,
                emp.department.name if emp.department else '',
                emp.designation.title if emp.designation else '',
                emp.status,
                emp.join_date
            ])
        
        return response
    export_to_csv.short_description = "Export to CSV"


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee', 'relationship', 'phone_number', 'is_primary')
    list_filter = ('relationship', 'is_primary', 'can_make_medical_decisions')
    search_fields = ['name', 'phone_number', 'employee__user__first_name', 'employee__user__last_name']


@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    list_display = ('employee', 'bank_name', 'account_number', 'account_type', 'is_verified')
    list_filter = ('bank_name', 'account_type', 'is_verified')
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'account_number']
    readonly_fields = ('is_verified', 'verified_at', 'verified_by')


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'employee', 'document_type', 'uploaded_at',
        'is_verified', 'expiry_status'
    )
    list_filter = ('document_type', 'is_verified', 'is_confidential', 'is_mandatory')
    search_fields = ['title', 'employee__user__first_name', 'employee__user__last_name', 'document_number']
    readonly_fields = ('uploaded_at', 'is_verified', 'verified_at', 'verified_by')
    date_hierarchy = 'uploaded_at'
    
    def expiry_status(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: #EF4444; font-weight: bold;">Expired</span>')
        elif obj.is_expiring_soon:
            return format_html('<span style="color: #F59E0B; font-weight: bold;">Expiring Soon</span>')
        return format_html('<span style="color: #10B981;">Valid</span>')
    expiry_status.short_description = 'Status'


@admin.register(Dependent)
class DependentAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee', 'relationship', 'age', 'is_on_medical_aid', 'is_tax_dependent')
    list_filter = ('relationship', 'is_on_medical_aid', 'is_tax_dependent', 'is_student')
    search_fields = ['name', 'employee__user__first_name', 'employee__user__last_name']


@admin.register(EmployeeNote)
class EmployeeNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'note_type', 'is_confidential', 'created_by', 'created_at')
    list_filter = ('note_type', 'is_confidential', 'created_at')
    search_fields = ['title', 'content', 'employee__user__first_name', 'employee__user__last_name']
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'