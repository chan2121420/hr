from django.db import models
from django.utils import timezone
from apps.employees.models import Employee
from apps.leaves.models import LeaveRequest
import math

class Shift(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    @property
    def expected_hours(self):
        start_delta = timezone.timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)
        end_delta = timezone.timedelta(hours=self.end_time.hour, minutes=self.end_time.minute)
        duration = end_delta - start_delta
        return duration.total_seconds() / 3600

class AttendanceRecord(models.Model):
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        ON_LEAVE = 'ON_LEAVE', 'On Leave'
        HOLIDAY = 'HOLIDAY', 'Holiday'
        PENDING = 'PENDING', 'Pending'

    employee = models.ForeignKey(Employee, related_name='attendance_records', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PENDING)
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True)
    
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} on {self.date} ({self.status})"

    @property
    def work_hours(self):
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            hours = duration.total_seconds() / 3600
            return round(hours, 2)
        return 0

    @property
    def overtime_hours(self):
        if not self.shift or self.work_hours == 0:
            return 0
        
        overtime = self.work_hours - self.shift.expected_hours
        return round(max(0, overtime), 2)