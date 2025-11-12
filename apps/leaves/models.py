from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee

class LeaveType(TimeStampedModel):
    """Types of leave"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    
    # Allocation
    days_allowed_per_year = models.DecimalField(max_digits=5, decimal_places=1)
    max_consecutive_days = models.IntegerField(null=True, blank=True)
    min_days_notice = models.IntegerField(default=7)
    
    # Properties
    is_paid = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    requires_document = models.BooleanField(default=False)
    can_be_carried_forward = models.BooleanField(default=False)
    max_carryforward_days = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    
    # Gender specific
    gender_specific = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('A', 'All')], default='A')
    
    is_active = models.BooleanField(default=True)
    color = models.CharField(max_length=7, default='#10B981')  # For calendar display
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class LeavePolicy(TimeStampedModel):
    """Company leave policies"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='policies')
    
    # Eligibility
    min_service_months = models.IntegerField(default=0)
    applies_to_employment_types = models.JSONField(default=list)  # ['permanent', 'contract']
    
    # Accrual
    accrual_method = models.CharField(
        max_length=20,
        choices=[
            ('yearly', 'Yearly'),
            ('monthly', 'Monthly Accrual'),
            ('quarterly', 'Quarterly'),
        ],
        default='yearly'
    )
    
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} - {self.leave_type.name}"

class LeaveBalance(TimeStampedModel):
    """Employee leave balances"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    
    # Balance
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    pending_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    carried_forward = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    
    class Meta:
        unique_together = ['employee', 'leave_type', 'year']
        ordering = ['-year']
    
    @property
    def available_days(self):
        return self.total_days - self.used_days - self.pending_days
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.name} ({self.year})"

class LeaveRequest(TimeStampedModel):
    """Leave applications"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(max_digits=5, decimal_places=1)
    
    # Details
    reason = models.TextField()
    contact_during_leave = models.CharField(max_length=100, blank=True)
    handover_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_handovers')
    
    # Approval workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Approvals (can have multiple levels)
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_approvals')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_comments = models.TextField(blank=True)
    
    rejected_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_rejections')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Document (if required)
    supporting_document = models.FileField(upload_to='leave_documents/', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    def has_sufficient_balance(self):
        """Check if employee has sufficient leave balance"""
        try:
            from datetime import date
            balance = LeaveBalance.objects.get(
                employee=self.employee,
                leave_type=self.leave_type,
                year=date.today().year
            )
            return balance.available_days >= self.days_requested
        except LeaveBalance.DoesNotExist:
            return False
 