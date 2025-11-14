from django.db import models
from django.conf import settings
from apps.employees.models import Employee
from datetime import timedelta

class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    default_days_allocated = models.PositiveIntegerField(default=20)
    is_paid = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Holiday(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField(unique=True)

    def __str__(self):
        return f"{self.name} ({self.date})"
    
    class Meta:
        ordering = ['date']

class LeaveRequest(models.Model):
    class LeaveStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED_BY_MANAGER = 'APPROVED_BY_MANAGER', 'Approved by Manager'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    
    reviewed_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_leaves'
    )
    review_comments = models.TextField(blank=True)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Leave for {self.employee} ({self.start_date} to {self.end_date})"

    @property
    def total_leave_days(self):
        holidays = Holiday.objects.filter(date__range=[self.start_date, self.end_date]).values_list('date', flat=True)
        
        days_count = 0
        current_date = self.start_date
        
        while current_date <= self.end_date:
            if current_date.weekday() < 5 and current_date not in holidays:
                days_count += 1
            current_date += timedelta(days=1)
            
        return days_count