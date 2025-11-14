from django.contrib import admin
from .models import Department, Designation, Employee, EmergencyContact, BankDetails, EmployeeDocument

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')
    search_fields = ('title',)

class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1

class BankDetailsInline(admin.StackedInline):
    model = BankDetails
    can_delete = False

class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 1

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id', 
        'user', 
        'department', 
        'designation', 
        'manager', 
        'status', 
        'join_date'
    )
    list_filter = ('status', 'employment_type', 'department', 'designation')
    search_fields = (
        'user__email', 
        'user__first_name', 
        'user__last_name', 
        'employee_id'
    )
    autocomplete_fields = ['user', 'manager']
    inlines = [BankDetailsInline, EmergencyContactInline, EmployeeDocumentInline]