from rest_framework import serializers
from .models import Department, Designation, Employee, EmergencyContact, BankDetails, EmployeeDocument
from apps.accounts.serializers import UserSerializer

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']

class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['id', 'title', 'description']

class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        exclude = ['employee']

class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        exclude = ['employee']

class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        exclude = ['employee']

class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    department = serializers.StringRelatedField()
    designation = serializers.StringRelatedField()
    manager = serializers.StringRelatedField()
    
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    bank_details = BankDetailsSerializer(read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_id',
            'user',
            'department',
            'designation',
            'manager',
            'join_date',
            'termination_date',
            'status',
            'employment_type',
            'emergency_contacts',
            'bank_details',
            'documents',
            'updated_at'
        ]

class EmployeeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'user',
            'department',
            'designation',
            'manager',
            'join_date',
            'status',
            'employment_type',
        ]