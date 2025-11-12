from rest_framework import serializers
from .models import Company, Department

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'registration_number', 'tax_number',
            'address', 'city', 'country', 'phone', 'email',
            'logo', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']

class DepartmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'company', 'company_name', 'name', 'code',
            'description', 'parent', 'manager', 'manager_name',
            'budget', 'is_active', 'employee_count', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_employee_count(self, obj):
        return obj.employees.filter(is_active=True).count()