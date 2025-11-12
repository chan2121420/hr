from rest_framework import serializers
from .models import (
    PayrollComponent, EmployeePayrollComponent, PayrollPeriod,
    Payslip, PayslipComponent, LoanAdvance
)

class PayrollComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollComponent
        fields = '__all__'

class EmployeePayrollComponentSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_type = serializers.CharField(source='component.component_type', read_only=True)
    
    class Meta:
        model = EmployeePayrollComponent
        fields = '__all__'

class PayrollPeriodSerializer(serializers.ModelSerializer):
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    payslip_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PayrollPeriod
        fields = '__all__'
    
    def get_payslip_count(self, obj):
        return obj.payslips.count()

class PayslipComponentSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_type = serializers.CharField(source='component.component_type', read_only=True)
    
    class Meta:
        model = PayslipComponent
        fields = ['id', 'component', 'component_name', 'component_type', 'amount']

class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_display = serializers.CharField(source='employee.employee_id', read_only=True)
    period_name = serializers.CharField(source='period.name', read_only=True)
    components = PayslipComponentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Payslip
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_display',
            'period', 'period_name', 'basic_salary', 'total_working_days',
            'days_worked', 'days_absent', 'total_earnings',
            'total_deductions', 'paye_tax', 'nssa_employee',
            'nssa_employer', 'gross_salary', 'net_salary', 'currency',
            'is_paid', 'payment_date', 'payment_method',
            'payment_reference', 'pdf_file', 'components', 'created_at'
        ]

class LoanAdvanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    balance = serializers.ReadOnlyField()
    
    class Meta:
        model = LoanAdvance
        fields = '__all__'