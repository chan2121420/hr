from rest_framework import serializers
from .models import Attendance, WorkSchedule, Holiday, AttendanceException

class WorkScheduleSerializer(serializers.ModelSerializer):
    total_hours = serializers.ReadOnlyField(source='total_hours_per_day')
    
    class Meta:
        model = WorkSchedule
        fields = '__all__'

class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_display = serializers.CharField(source='employee.employee_id', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_display',
            'date', 'clock_in', 'clock_out', 'clock_in_location',
            'clock_out_location', 'status', 'is_late', 'late_by_minutes',
            'hours_worked', 'overtime_hours', 'break_time', 'notes',
            'approved_by', 'created_at'
        ]
        read_only_fields = ['hours_worked', 'overtime_hours', 'created_at']

class AttendanceClockSerializer(serializers.Serializer):
    """Serializer for clock in/out actions"""
    location = serializers.CharField(max_length=200, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

class AttendanceExceptionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = AttendanceException
        fields = '__all__'

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'