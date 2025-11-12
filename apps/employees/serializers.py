from rest_framework import serializers
from .models import (
    Employee, Position, JobLevel, EmployeeSkill,
    EmployeeDocument, EmployeeDependant
)

class JobLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLevel
        fields = '__all__'

class PositionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    job_level_name = serializers.CharField(source='job_level.name', read_only=True)
    
    class Meta:
        model = Position
        fields = [
            'id', 'company', 'title', 'code', 'department',
            'department_name', 'job_level', 'job_level_name',
            'description', 'responsibilities', 'requirements',
            'reports_to', 'is_active'
        ]

class EmployeeSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSkill
        fields = [
            'id', 'employee', 'skill_name', 'proficiency',
            'years_experience', 'certified', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at']

class EmployeeDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = EmployeeDocument
        fields = [
            'id', 'employee', 'document_type', 'title', 'file',
            'expiry_date', 'uploaded_by', 'uploaded_by_name',
            'notes', 'is_verified', 'verified_by', 'verified_at',
            'uploaded_at'
        ]
        read_only_fields = ['uploaded_at', 'verified_at']

class EmployeeDependantSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployeeDependant
        fields = [
            'id', 'employee', 'first_name', 'last_name',
            'date_of_birth', 'age', 'relationship',
            'national_id', 'is_beneficiary'
        ]
    
    def get_age(self, obj):
        from datetime import date
        today = date.today()
        return today.year - obj.date_of_birth.year

class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing employees"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'first_name', 'last_name',
            'work_email', 'phone_number', 'department', 'department_name',
            'position', 'position_title', 'manager', 'manager_name',
            'employment_type', 'is_active', 'photo'
        ]

class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single employee view"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    age = serializers.ReadOnlyField()
    years_of_service = serializers.ReadOnlyField()
    
    skills = EmployeeSkillSerializer(many=True, read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)
    dependants = EmployeeDependantSerializer(many=True, read_only=True)
    
    class Meta:
        model = Employee
        fields = '__all__'

class EmployeeCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating employees"""
    
    class Meta:
        model = Employee
        exclude = ['created_at', 'updated_at']
    
    def validate_work_email(self, value):
        """Ensure work email is unique"""
        if self.instance:
            if Employee.objects.exclude(pk=self.instance.pk).filter(work_email=value).exists():
                raise serializers.ValidationError("This email is already in use")
        else:
            if Employee.objects.filter(work_email=value).exists():
                raise serializers.ValidationError("This email is already in use")
        return value