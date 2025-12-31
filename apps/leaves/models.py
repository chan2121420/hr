from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.employees.models import Employee
from datetime import timedelta, date
from decimal import Decimal
import uuid


class LeaveType(models.Model):
    """Enhanced leave types - Zimbabwe Labour Act compliant"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    
    # Allocation
    default_days_allocated = models.PositiveIntegerField(
        default=22,
        validators=[MinValueValidator(0)],
        help_text="Annual leave days (Zimbabwe: 22 working days per year)"
    )
    max_days_allowed = models.PositiveIntegerField(
        default=30,
        help_text="Maximum days that can be taken at once"
    )
    min_days_allowed = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal('0.5'),
        help_text="Minimum days that can be requested"
    )
    
    # Leave properties
    is_paid = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    requires_manager_approval = models.BooleanField(default=True)
    requires_hr_approval = models.BooleanField(default=False)
    requires_document = models.BooleanField(
        default=False,
        help_text="Requires supporting documentation"
    )
    
    # Carryforward settings
    can_be_carried_forward = models.BooleanField(default=True)
    max_carry_forward_days = models.PositiveIntegerField(
        default=5,
        help_text="Maximum days that can be carried to next year"
    )
    carry_forward_expiry_months = models.PositiveIntegerField(
        default=3,
        help_text="Months before carried forward days expire"
    )
    
    # Accrual settings
    accrues_monthly = models.BooleanField(
        default=False,
        help_text="Leave accrues monthly vs annual allocation"
    )
    accrual_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Days accrued per month if monthly accrual"
    )
    
    # Gender-specific
    gender_specific = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female'), ('N', 'Neutral')],
        default='N'
    )
    
    # Eligibility
    min_service_months = models.PositiveIntegerField(
        default=0,
        help_text="Minimum months of service required"
    )
    applies_to_probation = models.BooleanField(
        default=False,
        help_text="Can be taken during probation period"
    )
    
    # Notice period
    notice_days_required = models.PositiveIntegerField(
        default=7,
        help_text="Days in advance the leave must be requested"
    )
    
    # Documentation requirements
    medical_certificate_required = models.BooleanField(default=False)
    medical_certificate_days_threshold = models.PositiveIntegerField(
        default=3,
        help_text="Days of leave before medical certificate required"
    )
    
    # Frequency restrictions
    max_requests_per_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of times this leave can be requested per year"
    )
    min_gap_days_between_requests = models.PositiveIntegerField(
        default=0,
        help_text="Minimum days between consecutive requests"
    )
    
    # Affects payroll
    affects_salary = models.BooleanField(
        default=False,
        help_text="Leave affects salary calculation"
    )
    salary_deduction_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Percentage of salary to deduct"
    )
    
    # Special leave types
    is_emergency_leave = models.BooleanField(default=False)
    is_study_leave = models.BooleanField(default=False)
    is_compassionate_leave = models.BooleanField(default=False)
    is_sabbatical = models.BooleanField(default=False)
    is_maternity_leave = models.BooleanField(default=False)
    is_paternity_leave = models.BooleanField(default=False)
    
    # Display settings
    color_code = models.CharField(
        max_length=7,
        default='#10B981',
        help_text="Hex color code for calendar display"
    )
    icon = models.CharField(max_length=50, default='fa-plane', help_text="Icon class name")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Leave Type')
        verbose_name_plural = _('Leave Types')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join([word[0] for word in self.name.split()[:3]]).upper()
        super().save(*args, **kwargs)

    def is_eligible(self, employee):
        """Check if employee is eligible for this leave type"""
        if employee.tenure_months < self.min_service_months:
            return False, "Insufficient service period"
        
        if employee.is_on_probation and not self.applies_to_probation:
            return False, "Not available during probation"
        
        if self.gender_specific != 'N':
            if hasattr(employee.user, 'profile'):
                if employee.user.profile.gender != self.gender_specific:
                    return False, "Gender-specific leave type"
        
        return True, "Eligible"


class Holiday(models.Model):
    """Zimbabwe public holidays and non-working days"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    date = models.DateField(unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    is_recurring = models.BooleanField(
        default=False,
        help_text="Holiday occurs every year on the same date"
    )
    is_optional = models.BooleanField(
        default=False,
        help_text="Optional holiday"
    )
    is_half_day = models.BooleanField(default=False)
    
    applies_to_all = models.BooleanField(default=True)
    departments = models.ManyToManyField(
        'employees.Department',
        blank=True,
        help_text="Specific departments this holiday applies to"
    )
    
    is_national_holiday = models.BooleanField(default=True)
    substitute_date = models.DateField(
        null=True,
        blank=True,
        help_text="If holiday falls on weekend, substitute date"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        verbose_name = _('Public Holiday')
        verbose_name_plural = _('Public Holidays')

    def __str__(self):
        return f"{self.name} ({self.date})"

    @property
    def is_upcoming(self):
        """Check if holiday is upcoming within 30 days"""
        days_until = (self.date - date.today()).days
        return 0 <= days_until <= 30

    @property
    def falls_on_weekend(self):
        """Check if holiday falls on weekend"""
        return self.date.weekday() >= 5


class LeaveBalance(models.Model):
    """Track leave balances for each employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances'
    )
    year = models.PositiveIntegerField()
    
    # Balance tracking
    total_allocated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    used = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    pending = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Leave requests awaiting approval"
    )
    carried_forward = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    carried_forward_expiry_date = models.DateField(null=True, blank=True)
    
    # Adjustments
    manual_adjustment = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Manual balance adjustments (+ or -)"
    )
    adjustment_reason = models.TextField(blank=True)
    adjusted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_adjustments'
    )
    adjusted_at = models.DateTimeField(null=True, blank=True)
    
    # Accrual tracking
    last_accrual_date = models.DateField(null=True, blank=True)
    next_accrual_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'leave_type', 'year')
        ordering = ['-year', 'employee']
        verbose_name = _('Leave Balance')
        verbose_name_plural = _('Leave Balances')
        indexes = [
            models.Index(fields=['employee', 'year']),
            models.Index(fields=['leave_type', 'year']),
        ]

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.year})"

    @property
    def available(self):
        """Calculate available leave balance"""
        total = (
            float(self.total_allocated) + 
            float(self.carried_forward) + 
            float(self.manual_adjustment)
        )
        used_and_pending = float(self.used) + float(self.pending)
        return round(max(0, total - used_and_pending), 2)

    @property
    def total_entitlement(self):
        """Total leave entitlement including carryforward"""
        return float(self.total_allocated) + float(self.carried_forward) + float(self.manual_adjustment)

    @property
    def utilization_percentage(self):
        """Percentage of leave utilized"""
        if self.total_entitlement > 0:
            return round((float(self.used) / self.total_entitlement) * 100, 2)
        return 0

    @property
    def is_overdrawn(self):
        """Check if employee has used more leave than allocated"""
        return self.available < 0

    def can_apply(self, days_requested):
        """Check if employee can apply for the requested days"""
        return self.available >= days_requested

    def accrue_monthly(self):
        """Accrue monthly leave if applicable"""
        if self.leave_type.accrues_monthly:
            self.total_allocated += self.leave_type.accrual_rate
            self.last_accrual_date = date.today()
            self.next_accrual_date = date.today() + timedelta(days=30)
            self.save()

    def adjust_balance(self, adjustment_days, reason, adjusted_by):
        """Manually adjust leave balance"""
        self.manual_adjustment += Decimal(str(adjustment_days))
        self.adjustment_reason = reason
        self.adjusted_by = adjusted_by
        self.adjusted_at = timezone.now()
        self.save()


class LeaveRequest(models.Model):
    """Enhanced leave requests"""
    
    class LeaveStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING = 'PENDING', _('Pending')
        MANAGER_APPROVED = 'MANAGER_APPROVED', _('Manager Approved')
        HR_APPROVED = 'HR_APPROVED', _('HR Approved')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        CANCELLED = 'CANCELLED', _('Cancelled')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn')
        EXPIRED = 'EXPIRED', _('Expired')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    reason = models.TextField()
    
    # Half day options
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(
        max_length=10,
        choices=[('AM', 'Morning'), ('PM', 'Afternoon')],
        blank=True,
        null=True
    )
    
    status = models.CharField(
        max_length=30,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
        db_index=True
    )
    
    # Supporting documents
    supporting_document = models.FileField(
        upload_to='leave_documents/%Y/%m/',
        blank=True,
        null=True
    )
    additional_documents = models.JSONField(
        default=list,
        blank=True
    )
    
    # Approval workflow
    manager_approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manager_approved_leaves'
    )
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    manager_comments = models.TextField(blank=True)
    
    hr_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_approved_leaves'
    )
    hr_approved_at = models.DateTimeField(null=True, blank=True)
    hr_comments = models.TextField(blank=True)
    
    final_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='final_approved_leaves'
    )
    final_approved_at = models.DateTimeField(null=True, blank=True)
    
    # Rejection
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_leaves'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Handover information
    handover_notes = models.TextField(blank=True)
    covering_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='covering_leaves'
    )
    covering_employee_notified = models.BooleanField(default=False)
    
    # Emergency contact
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    
    # Return to work
    actual_return_date = models.DateField(null=True, blank=True)
    return_to_work_completed = models.BooleanField(default=False)
    early_return = models.BooleanField(default=False)
    late_return = models.BooleanField(default=False)
    late_return_reason = models.TextField(blank=True)
    
    # Cancellation
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_leaves'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    # Notifications
    employee_notified = models.BooleanField(default=False)
    manager_notified = models.BooleanField(default=False)
    hr_notified = models.BooleanField(default=False)
    
    # Priority
    is_urgent = models.BooleanField(default=False)
    is_emergency = models.BooleanField(default=False)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', 'requested_at']),
        ]
        verbose_name = _('Leave Request')
        verbose_name_plural = _('Leave Requests')

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.start_date} to {self.end_date})"

    def clean(self):
        """Validate leave request"""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError('End date must be after start date')
            
            if self.start_date < date.today() and not self.pk and not self.is_emergency:
                raise ValidationError('Cannot request leave for past dates')
            
            if hasattr(self, 'leave_type') and self.leave_type and not self.is_emergency:
                days_until_start = (self.start_date - date.today()).days
                if days_until_start < self.leave_type.notice_days_required and not self.pk:
                    raise ValidationError(
                        f'Leave must be requested at least {self.leave_type.notice_days_required} days in advance'
                    )
        
        if self.is_half_day and not self.half_day_period:
            raise ValidationError('Half day period must be specified')
        
        if self.is_half_day and self.start_date != self.end_date:
            raise ValidationError('Half day leave can only be for a single day')

    def save(self, *args, **kwargs):
        self.full_clean()
        
        if self.pk:
            old_instance = LeaveRequest.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                self._update_leave_balance(old_instance.status)
        
        super().save(*args, **kwargs)

    def _update_leave_balance(self, old_status):
        """Update leave balance based on status change"""
        from django.db.models import F
        
        year = self.start_date.year
        balance, _ = LeaveBalance.objects.get_or_create(
            employee=self.employee,
            leave_type=self.leave_type,
            year=year,
            defaults={'total_allocated': self.leave_type.default_days_allocated}
        )
        
        days = Decimal(str(self.total_leave_days))
        
        if old_status == 'PENDING' and self.status == 'APPROVED':
            balance.pending = F('pending') - days
            balance.used = F('used') + days
        elif old_status == 'PENDING' and self.status in ['REJECTED', 'CANCELLED', 'WITHDRAWN']:
            balance.pending = F('pending') - days
        elif old_status == 'APPROVED' and self.status in ['CANCELLED', 'WITHDRAWN']:
            balance.used = F('used') - days
        elif self.status == 'PENDING' and not old_status:
            balance.pending = F('pending') + days
        
        balance.save()

    @property
    def total_leave_days(self):
        """Calculate total leave days"""
        if not self.start_date or not self.end_date:
            return 0
        
        if self.is_half_day:
            return 0.5
        
        return calculate_working_days(self.start_date, self.end_date)

    @property
    def is_overlapping(self):
        """Check if overlaps with another approved leave"""
        from django.db.models import Q
        
        overlapping = LeaveRequest.objects.filter(
            employee=self.employee,
            status__in=['APPROVED', 'MANAGER_APPROVED', 'HR_APPROVED'],
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )
        
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)
        
        return overlapping.exists()

    @property
    def days_until_start(self):
        if self.start_date:
            return (self.start_date - date.today()).days
        return None

    @property
    def is_current(self):
        today = date.today()
        return self.start_date <= today <= self.end_date and self.status == 'APPROVED'

    @property
    def is_upcoming(self):
        if self.start_date and self.status == 'APPROVED':
            days_until = (self.start_date - date.today()).days
            return 0 < days_until <= 7
        return False

    @property
    def requires_medical_certificate(self):
        if self.leave_type.medical_certificate_required:
            return self.total_leave_days >= self.leave_type.medical_certificate_days_threshold
        return False

    def approve_by_manager(self, manager, comments=''):
        self.status = self.LeaveStatus.MANAGER_APPROVED
        self.manager_approved_by = manager
        self.manager_approved_at = timezone.now()
        self.manager_comments = comments
        
        if not self.leave_type.requires_hr_approval:
            self.status = self.LeaveStatus.APPROVED
            self.final_approved_at = timezone.now()
        
        self.save()

    def approve_by_hr(self, user, comments=''):
        self.status = self.LeaveStatus.APPROVED
        self.hr_approved_by = user
        self.hr_approved_at = timezone.now()
        self.hr_comments = comments
        self.final_approved_at = timezone.now()
        self.save()

    def reject(self, user, reason=''):
        self.status = self.LeaveStatus.REJECTED
        self.rejected_by = user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def cancel(self, user, reason=''):
        if self.status in ['APPROVED', 'MANAGER_APPROVED', 'HR_APPROVED']:
            self.status = self.LeaveStatus.CANCELLED
            self.cancelled_by = user
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.save()
        else:
            raise ValidationError('Only approved leave can be cancelled')

    def withdraw(self):
        if self.status == 'PENDING':
            self.status = self.LeaveStatus.WITHDRAWN
            self.save()
        else:
            raise ValidationError('Only pending leave requests can be withdrawn')


class LeaveEncashment(models.Model):
    """Leave encashment - converting unused leave to cash"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_encashments'
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    year = models.PositiveIntegerField()
    
    days_encashed = models.DecimalField(max_digits=5, decimal_places=2)
    rate_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('PROCESSED', 'Processed'),
            ('PAID', 'Paid'),
            ('REJECTED', 'Rejected'),
        ],
        default='PENDING'
    )
    
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']
        unique_together = ('employee', 'leave_type', 'year')
        verbose_name = _('Leave Encashment')
        verbose_name_plural = _('Leave Encashments')

    def __str__(self):
        return f"{self.employee} - {self.days_encashed} days ({self.year})"

    def save(self, *args, **kwargs):
        self.total_amount = self.days_encashed * self.rate_per_day
        super().save(*args, **kwargs)


def calculate_working_days(start_date, end_date):
    """Calculate working days excluding weekends and public holidays"""
    holidays = Holiday.objects.filter(
        date__range=[start_date, end_date],
        applies_to_all=True
    ).values_list('date', flat=True)
    
    days_count = 0
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in holidays:
            days_count += 1
        current_date += timedelta(days=1)
    
    return days_count