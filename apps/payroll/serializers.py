from rest_framework import serializers
from .models import SalaryComponent, EmployeeSalary, Payslip, PayslipEntry

class SalaryComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponent
        fields = '__all__'

class EmployeeSalarySerializer(serializers.ModelSerializer):
    component = serializers.StringRelatedField()
    component_id = serializers.PrimaryKeyRelatedField(
        queryset=SalaryComponent.objects.all(),
        source='component',
        write_only=True
    )
    
    class Meta:
        model = EmployeeSalary
        fields = ['id', 'component', 'component_id', 'amount']

class PayslipEntrySerializer(serializers.ModelSerializer):
    component = serializers.StringRelatedField()
    
    class Meta:
        model = PayslipEntry
        fields = ['component', 'amount']

class PayslipSerializer(serializers.ModelSerializer):
    employee = serializers.StringRelatedField()
    entries = PayslipEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = Payslip
        fields = [
            'id', 
            'employee', 
            'pay_period_start', 
            'pay_period_end', 
            'status',
            'gross_earnings',
            'total_deductions',
            'net_pay',
            'generated_at',
            'entries'
        ]

class PayrollRunSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2020)