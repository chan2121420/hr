from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee
from datetime import datetime, timedelta

class WorkSchedule(TimeStampedModel):
    """Work schedules for employees"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Work days
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    
    # Work hours
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration = models.IntegerField(default=60)  # in minutes
    
    # Flexibility
    flexible_hours = models.BooleanField(default=False)
    core_hours_start = models.TimeField(null=True, blank=True)
    core_hours_end = models.TimeField(null=True, blank=True)
    
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    @property
    def total_hours_per_day(self):
        """Calculate total working hours per day"""
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        duration = (end - start).seconds / 3600
        return duration - (self.break_duration / 60)

class EmployeeSchedule(TimeStampedModel):
    """Employee-specific work schedules"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='work_schedules')
    schedule = models.ForeignKey(WorkSchedule, on_delete=models.CASCADE)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-effective_from']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.schedule.name}"

class Attendance(TimeStampedModel):
    """Daily attendance records"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
        ('weekend', 'Weekend'),
        ('holiday', 'Public Holiday'),
        ('wfh', 'Work From Home'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    
    # Clock in/out
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    clock_in_location = models.CharField(max_length=200, blank=True)
    clock_out_location = models.CharField(max_length=200, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    is_late = models.BooleanField(default=False)
    late_by_minutes = models.IntegerField(default=0)
    
    # Hours calculation
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_time = models.IntegerField(default=0)  # in minutes
    
    # Notes
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['employee', '-date']),
            models.Index(fields=['date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date} ({self.status})"
    
    def calculate_hours(self):
        """Calculate hours worked"""
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            hours = duration.total_seconds() / 3600
            break_hours = self.break_time / 60
            self.hours_worked = round(hours - break_hours, 2)
            
            # Calculate overtime (if worked more than 8 hours)
            if self.hours_worked > 8:
                self.overtime_hours = self.hours_worked - 8
            
            self.save()

class AttendanceException(TimeStampedModel):
    """Attendance exceptions and regularization requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_exceptions')
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='exceptions')
    reason = models.TextField()
    requested_clock_in = models.DateTimeField(null=True, blank=True)
    requested_clock_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    review_comments = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Exception: {self.employee.get_full_name()} - {self.attendance.date}"

class Holiday(TimeStampedModel):
    """Public holidays"""
    name = models.CharField(max_length=200)
    date = models.DateField()
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['date']
        unique_together = ['name', 'date']
    
    def __str__(self):
        return f"{self.name} - {self.date}"
