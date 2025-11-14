from django.contrib import admin
from .models import SalaryComponent, EmployeeSalary, Payslip, PayslipEntry

@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_taxable', 'is_statutory')
    list_filter = ('type', 'is_taxable', 'is_statutory')

class EmployeeSalaryInline(admin.TabularInline):
    model = EmployeeSalary
    extra = 1

class PayslipEntryInline(admin.TabularInline):
    model = PayslipEntry
    extra = 0
    readonly_fields = ('component', 'amount')
    can_delete = False

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'pay_period_start', 'pay_period_end', 'net_pay', 'status')
    list_filter = ('status', 'pay_period_start')
    search_fields = ('employee__user__email',)
    inlines = [PayslipEntryInline]