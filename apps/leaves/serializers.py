from rest_framework import serializers
from .models import LeaveType, Holiday, LeaveBalance, LeaveRequest, LeaveEncashment
from apps.employees.serializers import EmployeeSerializer


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            'id', 'name', 'code', 'description',
            'default_days_allocated', 'max_days_allowed', 'min_days_allowed',
            'is_paid', 'requires_approval', 'color_code', 'icon',
            'is_active'
        ]


class LeaveTypeDetailSerializer(LeaveTypeSerializer):
    class Meta(LeaveTypeSerializer.Meta):
        fields = LeaveTypeSerializer.Meta.fields + [
            'requires_manager_approval', 'requires_hr_approval', 'requires_document',
            'can_be_carried_forward', 'max_carry_forward_days', 'carry_forward_expiry_months',
            'accrues_monthly', 'accrual_rate', 'gender_specific',
            'min_service_months', 'applies_to_probation', 'notice_days_required',
            'medical_certificate_required', 'medical_certificate_days_threshold',
            'max_requests_per_year', 'min_gap_days_between_requests',
            'affects_salary', 'salary_deduction_percentage',
            'is_emergency_leave', 'is_study_leave', 'is_compassionate_leave',
            'is_sabbatical', 'is_maternity_leave', 'is_paternity_leave'
        ]


class HolidaySerializer(serializers.ModelSerializer):
    is_upcoming = serializers.ReadOnlyField()
    falls_on_weekend = serializers.ReadOnlyField()
    
    class Meta:
        model = Holiday
        fields = [
            'id', 'name', 'date', 'description',
            'is_recurring', 'is_optional', 'is_half_day',
            'applies_to_all', 'is_national_holiday', 'substitute_date',
            'is_upcoming', 'falls_on_weekend'
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    available = serializers.ReadOnlyField()
    total_entitlement = serializers.ReadOnlyField()
    utilization_percentage = serializers.ReadOnlyField()
    is_overdrawn = serializers.ReadOnlyField()
    
    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'employee_name', 'leave_type', 'leave_type_name',
            'leave_type_code', 'year', 'total_allocated', 'used', 'pending',
            'carried_forward', 'carried_forward_expiry_date',
            'manual_adjustment', 'adjustment_reason',
            'available', 'total_entitlement', 'utilization_percentage', 'is_overdrawn',
            'last_accrual_date', 'next_accrual_date', 'updated_at'
        ]
        read_only_fields = ['employee', 'used', 'pending']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_color = serializers.CharField(source='leave_type.color_code', read_only=True)
    total_leave_days = serializers.ReadOnlyField()
    is_overlapping = serializers.ReadOnlyField()
    days_until_start = serializers.ReadOnlyField()
    is_current = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    requires_medical_certificate = serializers.ReadOnlyField()
    
    # Write-only field for creating requests
    leave_type_id = serializers.PrimaryKeyRelatedField(
        queryset=LeaveType.objects.all(),
        source='leave_type',
        write_only=True
    )
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_id',
            'leave_type', 'leave_type_id', 'leave_type_name', 'leave_type_color',
            'start_date', 'end_date', 'reason', 'status',
            'is_half_day', 'half_day_period',
            'total_leave_days', 'is_overlapping', 'days_until_start',
            'is_current', 'is_upcoming', 'requires_medical_certificate',
            'is_urgent', 'is_emergency',
            'requested_at', 'updated_at'
        ]
        read_only_fields = ['employee', 'status', 'requested_at']
    
    def validate(self, data):
        # Validate dates
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError("End date must be after start date")
        
        # Validate half day
        if data.get('is_half_day'):
            if not data.get('half_day_period'):
                raise serializers.ValidationError("Half day period must be specified")
            if data.get('start_date') != data.get('end_date'):
                raise serializers.ValidationError("Half day leave must be for a single day")
        
        return data


class LeaveRequestDetailSerializer(LeaveRequestSerializer):
    manager_approved_by_name = serializers.CharField(
        source='manager_approved_by.full_name',
        read_only=True
    )
    hr_approved_by_name = serializers.CharField(
        source='hr_approved_by.get_full_name',
        read_only=True
    )
    covering_employee_name = serializers.CharField(
        source='covering_employee.full_name',
        read_only=True
    )
    rejected_by_name = serializers.CharField(
        source='rejected_by.get_full_name',
        read_only=True
    )
    
    class Meta(LeaveRequestSerializer.Meta):
        fields = LeaveRequestSerializer.Meta.fields + [
            'supporting_document', 'additional_documents',
            'manager_approved_by', 'manager_approved_by_name', 'manager_approved_at', 'manager_comments',
            'hr_approved_by', 'hr_approved_by_name', 'hr_approved_at', 'hr_comments',
            'rejected_by', 'rejected_by_name', 'rejected_at', 'rejection_reason',
            'handover_notes', 'covering_employee', 'covering_employee_name',
            'emergency_contact_name', 'emergency_contact_phone',
            'actual_return_date', 'return_to_work_completed',
            'early_return', 'late_return', 'late_return_reason',
            'cancelled_by', 'cancelled_at', 'cancellation_reason'
        ]


class LeaveApprovalSerializer(serializers.Serializer):
    review_comments = serializers.CharField(required=False, allow_blank=True)


class LeaveEncashmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = LeaveEncashment
        fields = [
            'id', 'employee', 'employee_name', 'leave_type', 'leave_type_name',
            'year', 'days_encashed', 'rate_per_day', 'total_amount',
            'status', 'requested_at', 'approved_by', 'approved_by_name',
            'approved_at', 'processed_at', 'payment_date', 'notes'
        ]
        read_only_fields = ['employee', 'total_amount', 'status']


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            'leave_type', 'start_date', 'end_date', 'reason',
            'is_half_day', 'half_day_period',
            'handover_notes', 'covering_employee',
            'emergency_contact_name', 'emergency_contact_phone',
            'is_urgent', 'is_emergency'
        ]
    
    def validate(self, data):
        # Check if employee has sufficient balance
        employee = self.context['request'].user.employee_profile
        leave_type = data['leave_type']
        
        # Calculate days
        from .models import calculate_working_days
        if data.get('is_half_day'):
            days_requested = 0.5
        else:
            days_requested = calculate_working_days(data['start_date'], data['end_date'])
        
        # Check balance
        try:
            balance = LeaveBalance.objects.get(
                employee=employee,
                leave_type=leave_type,
                year=data['start_date'].year
            )
            if not balance.can_apply(days_requested):
                raise serializers.ValidationError(
                    f"Insufficient leave balance. Available: {balance.available} days"
                )
        except LeaveBalance.DoesNotExist:
            # Create balance if it doesn't exist
            LeaveBalance.objects.create(
                employee=employee,
                leave_type=leave_type,
                year=data['start_date'].year,
                total_allocated=leave_type.default_days_allocated
            )
        
        return data