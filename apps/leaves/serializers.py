from rest_framework import serializers
from .models import LeaveType, Holiday, LeaveRequest
from apps.employees.models import Employee

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'default_days_allocated', 'is_paid']

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'name', 'date']

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee = serializers.StringRelatedField()
    leave_type = serializers.StringRelatedField()
    reviewed_by = serializers.StringRelatedField(read_only=True)
    total_leave_days = serializers.ReadOnlyField()
    
    leave_type_id = serializers.PrimaryKeyRelatedField(
        queryset=LeaveType.objects.all(), 
        source='leave_type', 
        write_only=True
    )

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 
            'employee', 
            'leave_type',
            'leave_type_id',
            'start_date', 
            'end_date',
            'reason', 
            'status', 
            'reviewed_by', 
            'review_comments',
            'requested_at',
            'total_leave_days'
        ]
        read_only_fields = ('employee', 'status', 'reviewed_by', 'requested_at')
    
    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("End date must be after start date.")
        
        # In a "perfect" system, you would check leave balance here.
        # e.g., check_balance(employee, leave_type, start_date, end_date)
        
        return data

class LeaveApprovalSerializer(serializers.Serializer):
    review_comments = serializers.CharField(required=False, allow_blank=True)