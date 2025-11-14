from rest_framework import serializers
from .models import Shift, AttendanceRecord
from django.utils import timezone

class ShiftSerializer(serializers.ModelSerializer):
    expected_hours = serializers.ReadOnlyField()

    class Meta:
        model = Shift
        fields = ['id', 'name', 'start_time', 'end_time', 'expected_hours']

class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee = serializers.StringRelatedField()
    shift = serializers.StringRelatedField()
    work_hours = serializers.ReadOnlyField()
    overtime_hours = serializers.ReadOnlyField()
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 
            'employee', 
            'date', 
            'status', 
            'shift', 
            'clock_in', 
            'clock_out', 
            'work_hours',
            'overtime_hours',
            'notes'
        ]

class ClockInSerializer(serializers.Serializer):
    pass 

class ClockOutSerializer(serializers.Serializer):
    pass