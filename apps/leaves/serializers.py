
from rest_framework import serializers
from .models import LeaveType, LeaveBalance, LeaveRequest, LeavePolicy

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'

class LeavePolicySerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    
    class Meta:
        model = LeavePolicy
        fields = '__all__'

class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    available_days = serializers.ReadOnlyField()
    
    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'employee_name', 'leave_type',
            'leave_type_name', 'year', 'total_days', 'used_days',
            'pending_days', 'carried_forward', 'available_days'
        ]

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    handover_to_name = serializers.CharField(source='handover_to.get_full_name', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'leave_type',
            'leave_type_name', 'start_date', 'end_date',
            'days_requested', 'reason', 'contact_during_leave',
            'handover_to', 'handover_to_name', 'status',
            'submitted_at', 'approved_by', 'approved_by_name',
            'approved_at', 'approval_comments', 'rejected_by',
            'rejected_at', 'rejection_reason', 'supporting_document',
            'created_at'
        ]
        read_only_fields = ['created_at', 'submitted_at', 'approved_at', 'rejected_at']
    
    def validate(self, data):
        """Validate leave request"""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("End date must be after start date")
        
        # Check if employee has sufficient balance
        employee = data['employee']
        leave_type = data['leave_type']
        
        from datetime import date
        try:
            balance = LeaveBalance.objects.get(
                employee=employee,
                leave_type=leave_type,
                year=date.today().year
            )
            if balance.available_days < data['days_requested']:
                raise serializers.ValidationError(
                    f"Insufficient leave balance. Available: {balance.available_days} days"
                )
        except LeaveBalance.DoesNotExist:
            raise serializers.ValidationError("Leave balance not found for this year")
        
        return data
