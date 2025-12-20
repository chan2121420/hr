from rest_framework import serializers
from .models import (
    Department, Designation, Employee, EmergencyContact,
    BankDetails, EmployeeDocument, Dependent, EmployeeNote
)
from apps.accounts.serializers import UserSerializer


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)
    budget_utilization_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    head_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'description', 'head', 'head_name',
            'parent_department', 'email', 'phone', 'location',
            'annual_budget', 'budget_used', 'budget_utilization_percentage',
            'employee_count', 'is_active', 'created_at', 'updated_at'
        ]
    
    def get_head_name(self, obj):
        return obj.head.full_name if obj.head else None


class DepartmentDetailSerializer(DepartmentSerializer):
    sub_departments = DepartmentSerializer(many=True, read_only=True)
    employees = serializers.SerializerMethodField()
    
    class Meta(DepartmentSerializer.Meta):
        fields = DepartmentSerializer.Meta.fields + ['sub_departments', 'employees']
    
    def get_employees(self, obj):
        employees = obj.employee_set.filter(status='ACTIVE')[:10]
        return EmployeeSerializer(employees, many=True).data


class DesignationSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(
        source='current_employee_count',
        read_only=True
    )
    salary_range = serializers.CharField(
        source='salary_range_display',
        read_only=True
    )
    reports_to_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Designation
        fields = [
            'id', 'title', 'code', 'description', 'level',
            'min_salary', 'max_salary', 'salary_range',
            'reports_to', 'reports_to_title',
            'required_education', 'required_experience_years',
            'required_skills', 'required_certifications',
            'employee_count', 'is_active', 'created_at'
        ]
    
    def get_reports_to_title(self, obj):
        return obj.reports_to.title if obj.reports_to else None


class DesignationDetailSerializer(DesignationSerializer):
    key_responsibilities = serializers.JSONField()
    next_level_designation_title = serializers.SerializerMethodField()
    
    class Meta(DesignationSerializer.Meta):
        fields = DesignationSerializer.Meta.fields + [
            'key_responsibilities', 'next_level_designation_title',
            'eligible_for_bonus', 'eligible_for_overtime', 'eligible_for_company_car'
        ]
    
    def get_next_level_designation_title(self, obj):
        return obj.next_level_designation.title if obj.next_level_designation else None


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'name', 'relationship', 'phone_number',
            'alternate_phone', 'email', 'address',
            'is_primary', 'can_make_medical_decisions'
        ]


class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = [
            'id', 'bank_name', 'account_number', 'account_holder_name',
            'branch_name', 'branch_code', 'account_type', 'swift_code',
            'has_mobile_money', 'mobile_money_provider', 'mobile_money_number',
            'is_verified', 'verified_at', 'updated_at'
        ]
        read_only_fields = ['is_verified', 'verified_at']


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    is_expiring_soon = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = EmployeeDocument
        fields = [
            'id', 'document_type', 'title', 'document', 'description',
            'document_number', 'issue_date', 'expiry_date',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'file_size_mb', 'is_verified', 'verified_at',
            'is_confidential', 'is_mandatory',
            'is_expiring_soon', 'is_expired'
        ]
        read_only_fields = ['uploaded_by', 'uploaded_at', 'is_verified', 'verified_at']
    
    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else None
    
    def get_file_size_mb(self, obj):
        return obj.file_size


class DependentSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Dependent
        fields = [
            'id', 'name', 'relationship', 'date_of_birth', 'age',
            'gender', 'national_id', 'is_on_medical_aid',
            'medical_aid_number', 'is_student', 'school_name',
            'is_tax_dependent'
        ]


class EmployeeNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployeeNote
        fields = [
            'id', 'title', 'content', 'note_type',
            'is_confidential', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at']
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_title = serializers.CharField(source='designation.title', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)
    tenure_years = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    is_on_probation = serializers.BooleanField(read_only=True)
    probation_days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'user', 'department', 'department_name',
            'designation', 'designation_title', 'manager', 'manager_name',
            'join_date', 'status', 'employment_type', 'work_email',
            'work_phone', 'work_location', 'current_salary',
            'tenure_years', 'is_on_probation', 'probation_days_remaining',
            'performance_rating', 'last_review_date', 'next_review_date',
            'created_at', 'updated_at'
        ]


class EmployeeDetailSerializer(EmployeeSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    bank_details = BankDetailsSerializer(read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)
    dependents = DependentSerializer(many=True, read_only=True)
    subordinate_count = serializers.IntegerField(read_only=True)
    is_manager = serializers.BooleanField(read_only=True)
    reporting_chain = serializers.SerializerMethodField()
    
    class Meta(EmployeeSerializer.Meta):
        fields = EmployeeSerializer.Meta.fields + [
            'national_id', 'tax_number', 'nssa_number', 'pension_number',
            'contract_start_date', 'contract_end_date', 'contract_type',
            'office_location', 'salary_currency', 'probation_end_date',
            'confirmation_date', 'last_promotion_date',
            'skills', 'certifications', 'languages',
            'is_remote_worker', 'is_union_member',
            'can_approve_expenses', 'can_recruit', 'can_approve_leave',
            'emergency_contacts', 'bank_details', 'documents', 'dependents',
            'subordinate_count', 'is_manager', 'reporting_chain',
            'onboarding_completed', 'notes'
        ]
    
    def get_reporting_chain(self, obj):
        chain = obj.get_reporting_chain()
        return [
            {
                'id': str(mgr.id),
                'name': mgr.full_name,
                'designation': mgr.designation.title if mgr.designation else None
            }
            for mgr in chain
        ]


class EmployeeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'user', 'department', 'designation', 'manager',
            'join_date', 'status', 'employment_type',
            'work_email', 'work_phone', 'work_location',
            'contract_start_date', 'contract_end_date', 'contract_type',
            'current_salary', 'salary_currency',
            'national_id', 'tax_number', 'nssa_number'
        ]
    
    def validate(self, data):
        if data.get('manager') == data.get('user'):
            raise serializers.ValidationError("Employee cannot be their own manager")
        return data


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'department', 'designation', 'manager', 'shift',
            'status', 'employment_type', 'work_email', 'work_phone',
            'work_location', 'office_location', 'current_salary',
            'performance_rating', 'last_review_date', 'next_review_date',
            'skills', 'certifications', 'languages',
            'can_approve_expenses', 'can_recruit', 'can_approve_leave',
            'can_approve_timesheets', 'notes'
        ]