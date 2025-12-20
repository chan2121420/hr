from rest_framework import serializers
from .models import (
    Shift, AttendanceRecord, AttendanceBreak, AttendanceException,
    AttendancePolicy, AttendanceSummary, PublicHoliday
)
from apps.employees.serializers import EmployeeSerializer


class ShiftSerializer(serializers.ModelSerializer):
    expected_hours = serializers.ReadOnlyField()
    working_days_count = serializers.ReadOnlyField()
    is_night_shift = serializers.ReadOnlyField()
    
    class Meta:
        model = Shift
        fields = [
            'id', 'name', 'code', 'start_time', 'end_time',
            'expected_hours', 'break_duration_minutes', 'has_paid_break',
            'grace_period_minutes', 'early_departure_grace_minutes',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'working_days_count', 'is_night_shift', 'shift_type',
            'overtime_threshold_minutes', 'overtime_multiplier',
            'color_code', 'is_active'
        ]


class ShiftDetailSerializer(ShiftSerializer):
    working_days = serializers.ReadOnlyField()
    employee_count = serializers.SerializerMethodField()
    
    class Meta(ShiftSerializer.Meta):
        fields = ShiftSerializer.Meta.fields + [
            'working_days', 'employee_count',
            'requires_geofencing', 'geofence_radius_meters',
            'allowed_locations'
        ]
    
    def get_employee_count(self, obj):
        return obj.employees.filter(status='ACTIVE').count()


class AttendanceBreakSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.ReadOnlyField()
    is_ongoing = serializers.ReadOnlyField()
    
    class Meta:
        model = AttendanceBreak
        fields = [
            'id', 'break_start', 'break_end', 'break_type',
            'duration_minutes', 'is_ongoing', 'location', 'notes'
        ]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    shift_name = serializers.CharField(source='shift.name', read_only=True)
    work_hours = serializers.ReadOnlyField()
    overtime_hours = serializers.ReadOnlyField()
    punctuality_score = serializers.ReadOnlyField()
    efficiency_score = serializers.ReadOnlyField()
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'employee', 'employee_name', 'employee_id',
            'date', 'status', 'shift', 'shift_name',
            'clock_in', 'clock_out', 'work_hours', 'overtime_hours',
            'is_late', 'late_minutes', 'is_early_departure', 'early_departure_minutes',
            'total_break_minutes', 'punctuality_score', 'efficiency_score',
            'is_remote', 'is_weekend_work', 'is_public_holiday_work',
            'is_verified', 'notes'
        ]


class AttendanceRecordDetailSerializer(AttendanceRecordSerializer):
    breaks = AttendanceBreakSerializer(many=True, read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    overtime_pay_multiplier = serializers.ReadOnlyField()
    
    class Meta(AttendanceRecordSerializer.Meta):
        fields = AttendanceRecordSerializer.Meta.fields + [
            'breaks', 'productive_hours', 'tasks_completed', 'work_summary',
            'work_quality_rating', 'approved_by', 'approved_by_name', 'approved_at',
            'clock_in_location', 'clock_out_location',
            'clock_in_ip', 'clock_out_ip', 'clock_in_device', 'clock_out_device',
            'clock_in_photo', 'clock_out_photo',
            'is_manually_entered', 'requires_verification',
            'is_outside_geofence', 'geofence_violation_distance',
            'overtime_pay_multiplier', 'created_at', 'updated_at'
        ]


class ClockInSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    location = serializers.CharField(max_length=200, required=False)
    is_remote = serializers.BooleanField(default=False)
    photo = serializers.ImageField(required=False)


class ClockOutSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    location = serializers.CharField(max_length=200, required=False)
    work_summary = serializers.CharField(required=False, allow_blank=True)
    tasks_completed = serializers.IntegerField(default=0)
    productive_hours = serializers.DecimalField(max_digits=4, decimal_places=2, default=0)
    photo = serializers.ImageField(required=False)


class AttendanceExceptionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    
    class Meta:
        model = AttendanceException
        fields = [
            'id', 'employee', 'employee_name', 'attendance_record',
            'exception_date', 'exception_type', 'reason', 'supporting_document',
            'status', 'proposed_clock_in', 'proposed_clock_out', 'proposed_status',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_comments',
            'is_urgent', 'created_at'
        ]
        read_only_fields = ['employee', 'status', 'reviewed_by', 'reviewed_at']


class AttendancePolicySerializer(serializers.ModelSerializer):
    is_currently_effective = serializers.ReadOnlyField()
    
    class Meta:
        model = AttendancePolicy
        fields = '__all__'


class AttendanceSummarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    absence_rate = serializers.ReadOnlyField()
    overall_score = serializers.ReadOnlyField()
    
    class Meta:
        model = AttendanceSummary
        fields = [
            'id', 'employee', 'employee_name', 'month', 'year',
            'total_working_days', 'present_days', 'absent_days', 'late_days',
            'half_days', 'leave_days', 'weekend_work_days', 'holiday_work_days',
            'total_work_hours', 'total_overtime_hours', 'total_break_hours',
            'total_late_minutes', 'average_work_hours_per_day',
            'attendance_percentage', 'punctuality_score', 'absence_rate',
            'overall_score', 'has_disciplinary_issues', 'disciplinary_notes',
            'generated_at'
        ]


class PublicHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicHoliday
        fields = [
            'id', 'name', 'date', 'is_recurring', 'description',
            'is_paid', 'pay_multiplier'
        ]