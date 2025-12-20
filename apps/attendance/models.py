from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.employees.models import Employee
from datetime import datetime, timedelta, time, date
from decimal import Decimal
import uuid


class Shift(models.Model):
    """Enhanced shift definitions with Zimbabwe-specific considerations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Break times
    break_duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Standard break duration in minutes (e.g., lunch break)"
    )
    has_paid_break = models.BooleanField(default=False)
    
    # Grace periods
    grace_period_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Minutes allowed after start time before marking late"
    )
    early_departure_grace_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Minutes allowed before end time for early departure"
    )
    
    # Working days
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    
    # Overtime settings
    overtime_threshold_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minutes after shift end before overtime kicks in"
    )
    overtime_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.5'),
        help_text="Overtime pay multiplier (e.g., 1.5 for time-and-a-half)"
    )
    
    # Color coding for UI
    color_code = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Hex color code for shift display"
    )
    
    # Shift type
    shift_type = models.CharField(
        max_length=20,
        choices=[
            ('DAY', 'Day Shift'),
            ('NIGHT', 'Night Shift'),
            ('ROTATING', 'Rotating Shift'),
            ('SPLIT', 'Split Shift'),
            ('FLEXIBLE', 'Flexible Shift'),
        ],
        default='DAY'
    )
    
    # Location restrictions
    allowed_locations = models.JSONField(default=list, blank=True)
    requires_geofencing = models.BooleanField(default=False)
    geofence_radius_meters = models.PositiveIntegerField(default=100)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']
        verbose_name = _('Shift')
        verbose_name_plural = _('Shifts')
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['start_time', 'end_time']),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    @property
    def expected_hours(self):
        """Calculate expected work hours for the shift"""
        start_delta = timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)
        end_delta = timedelta(hours=self.end_time.hour, minutes=self.end_time.minute)
        
        # Handle shifts that cross midnight
        if end_delta < start_delta:
            end_delta += timedelta(days=1)
        
        duration = end_delta - start_delta
        
        # Subtract break if not paid
        if not self.has_paid_break:
            duration -= timedelta(minutes=self.break_duration_minutes)
        
        return round(duration.total_seconds() / 3600, 2)

    @property
    def is_night_shift(self):
        """Check if this is a night shift (crosses midnight)"""
        return self.end_time < self.start_time

    @property
    def working_days(self):
        """Return list of working days"""
        days = []
        if self.monday: days.append('Monday')
        if self.tuesday: days.append('Tuesday')
        if self.wednesday: days.append('Wednesday')
        if self.thursday: days.append('Thursday')
        if self.friday: days.append('Friday')
        if self.saturday: days.append('Saturday')
        if self.sunday: days.append('Sunday')
        return days

    @property
    def working_days_count(self):
        """Count of working days per week"""
        return len(self.working_days)

    def is_working_day(self, date_obj):
        """Check if given date is a working day for this shift"""
        day_map = {
            0: self.monday, 1: self.tuesday, 2: self.wednesday,
            3: self.thursday, 4: self.friday, 5: self.saturday, 6: self.sunday,
        }
        return day_map.get(date_obj.weekday(), False)


class PublicHoliday(models.Model):
    """Track Zimbabwe public holidays"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    date = models.DateField(db_index=True)
    is_recurring = models.BooleanField(
        default=True,
        help_text="If True, holiday recurs annually on same date"
    )
    description = models.TextField(blank=True)
    is_paid = models.BooleanField(
        default=True,
        help_text="If True, employees get paid for this holiday"
    )
    pay_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('2.5'),
        help_text="Pay multiplier if working on this holiday"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']
        unique_together = ('name', 'date')
        verbose_name = _('Public Holiday')
        verbose_name_plural = _('Public Holidays')

    def __str__(self):
        return f"{self.name} - {self.date}"


class AttendanceRecord(models.Model):
    """Enhanced daily attendance records"""
    
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'PRESENT', _('Present')
        ABSENT = 'ABSENT', _('Absent')
        ON_LEAVE = 'ON_LEAVE', _('On Leave')
        HOLIDAY = 'HOLIDAY', _('Holiday')
        LATE = 'LATE', _('Late')
        HALF_DAY = 'HALF_DAY', _('Half Day')
        PENDING = 'PENDING', _('Pending')
        WEEKEND = 'WEEKEND', _('Weekend')
        OVERTIME = 'OVERTIME', _('Overtime')
        SICK_LEAVE = 'SICK_LEAVE', _('Sick Leave')
        UNAUTHORIZED = 'UNAUTHORIZED', _('Unauthorized Absence')
        WORK_FROM_HOME = 'WORK_FROM_HOME', _('Work From Home')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        related_name='attendance_records',
        on_delete=models.CASCADE
    )
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PENDING
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Clock times
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    
    # Multiple break tracking
    total_break_minutes = models.PositiveIntegerField(default=0)
    
    # Calculated fields
    is_late = models.BooleanField(default=False)
    late_minutes = models.PositiveIntegerField(default=0)
    is_early_departure = models.BooleanField(default=False)
    early_departure_minutes = models.PositiveIntegerField(default=0)
    
    # Location tracking
    clock_in_location = models.CharField(max_length=200, blank=True)
    clock_out_location = models.CharField(max_length=200, blank=True)
    clock_in_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    clock_in_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    clock_out_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    clock_out_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    
    # IP and device tracking
    clock_in_ip = models.GenericIPAddressField(null=True, blank=True)
    clock_out_ip = models.GenericIPAddressField(null=True, blank=True)
    clock_in_device = models.CharField(max_length=200, blank=True)
    clock_out_device = models.CharField(max_length=200, blank=True)
    clock_in_user_agent = models.TextField(blank=True)
    clock_out_user_agent = models.TextField(blank=True)
    
    # Biometric/photo verification
    clock_in_photo = models.ImageField(
        upload_to='attendance_photos/%Y/%m/',
        null=True,
        blank=True
    )
    clock_out_photo = models.ImageField(
        upload_to='attendance_photos/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Work details
    productive_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Self-reported productive hours"
    )
    tasks_completed = models.PositiveIntegerField(default=0)
    work_summary = models.TextField(blank=True, null=True)
    work_quality_rating = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    
    notes = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_attendance_records'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Flags
    is_remote = models.BooleanField(default=False)
    is_weekend_work = models.BooleanField(default=False)
    is_public_holiday_work = models.BooleanField(default=False)
    requires_verification = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_manually_entered = models.BooleanField(default=False)
    
    # Geofencing
    is_outside_geofence = models.BooleanField(default=False)
    geofence_violation_distance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance from allowed location in meters"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_attendance_records'
    )

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date', 'employee']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
            models.Index(fields=['shift', 'date']),
            models.Index(fields=['is_verified', 'requires_verification']),
        ]
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')

    def __str__(self):
        return f"{self.employee} on {self.date} ({self.status})"

    def clean(self):
        """Validate attendance record"""
        if self.clock_out and self.clock_in:
            if self.clock_out <= self.clock_in:
                raise ValidationError('Clock out time must be after clock in time')
        
        # Check if date is in the future
        if self.date > date.today():
            raise ValidationError('Cannot create attendance for future dates')

    def save(self, *args, **kwargs):
        # Check if late
        if self.clock_in and self.shift:
            scheduled_start = datetime.combine(self.date, self.shift.start_time)
            scheduled_start = timezone.make_aware(scheduled_start)
            
            grace_period = timedelta(minutes=self.shift.grace_period_minutes)
            if self.clock_in > scheduled_start + grace_period:
                self.is_late = True
                self.late_minutes = int((self.clock_in - scheduled_start).total_seconds() / 60)
                if self.status == 'PENDING':
                    self.status = 'LATE'
        
        # Check for early departure
        if self.clock_out and self.shift:
            scheduled_end = datetime.combine(self.date, self.shift.end_time)
            scheduled_end = timezone.make_aware(scheduled_end)
            
            if self.shift.is_night_shift:
                scheduled_end += timedelta(days=1)
            
            grace_period = timedelta(minutes=self.shift.early_departure_grace_minutes)
            if self.clock_out < scheduled_end - grace_period:
                self.is_early_departure = True
                self.early_departure_minutes = int(
                    (scheduled_end - self.clock_out).total_seconds() / 60
                )
        
        # Update status
        if self.clock_in and self.clock_out and self.status == 'PENDING':
            if self.overtime_hours > 0:
                self.status = 'OVERTIME'
            elif not self.is_late:
                self.status = 'PRESENT'
        
        # Check if weekend work
        if self.date.weekday() >= 5:
            self.is_weekend_work = True
        
        # Check for public holiday
        if PublicHoliday.objects.filter(date=self.date).exists():
            self.is_public_holiday_work = True
        
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def work_hours(self):
        """Calculate total work hours"""
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            
            # Subtract break time
            if self.total_break_minutes:
                duration -= timedelta(minutes=self.total_break_minutes)
            
            hours = duration.total_seconds() / 3600
            return round(max(0, hours), 2)
        return 0

    @property
    def overtime_hours(self):
        """Calculate overtime hours"""
        if not self.shift or self.work_hours == 0:
            return 0
        
        overtime = self.work_hours - self.shift.expected_hours
        return round(max(0, overtime), 2)

    @property
    def overtime_pay_multiplier(self):
        """Get overtime pay multiplier"""
        multiplier = Decimal('1.5')
        
        if self.shift:
            multiplier = self.shift.overtime_multiplier
        
        if self.is_weekend_work:
            multiplier = Decimal('2.0')
        
        if self.is_public_holiday_work:
            holiday = PublicHoliday.objects.filter(date=self.date).first()
            if holiday:
                multiplier = holiday.pay_multiplier
            else:
                multiplier = Decimal('2.5')
        
        return multiplier

    @property
    def efficiency_score(self):
        """Calculate work efficiency score"""
        if self.work_hours > 0 and self.productive_hours:
            return round((float(self.productive_hours) / self.work_hours) * 100, 2)
        return 0

    @property
    def punctuality_score(self):
        """Calculate punctuality score (0-100)"""
        if not self.clock_in:
            return 0
        
        if not self.is_late and not self.is_early_departure:
            return 100
        
        penalties = self.late_minutes + self.early_departure_minutes
        score = max(0, 100 - (penalties * 2))
        return round(score, 2)

    def calculate_pay(self, hourly_rate):
        """Calculate total pay for this attendance record"""
        if not hourly_rate:
            return Decimal('0')
        
        regular_hours = min(self.work_hours, self.shift.expected_hours if self.shift else 8)
        regular_pay = Decimal(str(regular_hours)) * hourly_rate
        
        overtime_pay = Decimal(str(self.overtime_hours)) * hourly_rate * self.overtime_pay_multiplier
        
        # Deduction for unauthorized absence
        if self.status in ['ABSENT', 'UNAUTHORIZED']:
            return Decimal('0')
        
        # Half day deduction
        if self.status == 'HALF_DAY':
            return regular_pay / 2
        
        return regular_pay + overtime_pay


class AttendanceBreak(models.Model):
    """Track individual break periods"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name='breaks'
    )
    break_start = models.DateTimeField()
    break_end = models.DateTimeField(null=True, blank=True)
    break_type = models.CharField(
        max_length=20,
        choices=[
            ('LUNCH', 'Lunch Break'),
            ('TEA', 'Tea Break'),
            ('PRAYER', 'Prayer Break'),
            ('PERSONAL', 'Personal Break'),
            ('MEDICAL', 'Medical Break'),
            ('SMOKING', 'Smoking Break'),
            ('OTHER', 'Other'),
        ],
        default='LUNCH'
    )
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['break_start']
        verbose_name = _('Attendance Break')
        verbose_name_plural = _('Attendance Breaks')

    def __str__(self):
        return f"{self.break_type} - {self.attendance_record}"

    @property
    def duration_minutes(self):
        """Calculate break duration in minutes"""
        if self.break_start and self.break_end:
            duration = self.break_end - self.break_start
            return int(duration.total_seconds() / 60)
        return 0

    @property
    def is_ongoing(self):
        """Check if break is still ongoing"""
        return self.break_start and not self.break_end

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update total break time
        if self.attendance_record and self.break_end:
            total_break = sum(
                b.duration_minutes for b in 
                self.attendance_record.breaks.filter(break_end__isnull=False)
            )
            self.attendance_record.total_break_minutes = total_break
            self.attendance_record.save(update_fields=['total_break_minutes'])


class AttendanceException(models.Model):
    """Track attendance exceptions and correction requests"""
    
    class ExceptionType(models.TextChoices):
        FORGOT_CLOCK_IN = 'FORGOT_CLOCK_IN', _('Forgot to Clock In')
        FORGOT_CLOCK_OUT = 'FORGOT_CLOCK_OUT', _('Forgot to Clock Out')
        LATE_ARRIVAL = 'LATE_ARRIVAL', _('Late Arrival')
        EARLY_DEPARTURE = 'EARLY_DEPARTURE', _('Early Departure')
        MISSED_DAY = 'MISSED_DAY', _('Missed Day')
        SYSTEM_ERROR = 'SYSTEM_ERROR', _('System Error')
        DEVICE_ISSUE = 'DEVICE_ISSUE', _('Device Issue')
        NETWORK_ISSUE = 'NETWORK_ISSUE', _('Network Issue')
        WRONG_LOCATION = 'WRONG_LOCATION', _('Wrong Location')
        OTHER = 'OTHER', _('Other')

    class ExceptionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_exceptions'
    )
    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name='exceptions',
        null=True,
        blank=True
    )
    exception_date = models.DateField()
    exception_type = models.CharField(
        max_length=20,
        choices=ExceptionType.choices
    )
    reason = models.TextField()
    supporting_document = models.FileField(
        upload_to='attendance_exceptions/%Y/%m/',
        null=True,
        blank=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=ExceptionStatus.choices,
        default=ExceptionStatus.PENDING
    )
    
    # Proposed corrections
    proposed_clock_in = models.DateTimeField(null=True, blank=True)
    proposed_clock_out = models.DateTimeField(null=True, blank=True)
    proposed_status = models.CharField(
        max_length=20,
        choices=AttendanceRecord.AttendanceStatus.choices,
        null=True,
        blank=True
    )
    
    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_exceptions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    
    is_urgent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Attendance Exception')
        verbose_name_plural = _('Attendance Exceptions')
        indexes = [
            models.Index(fields=['employee', 'exception_date']),
            models.Index(fields=['status', 'is_urgent']),
        ]

    def __str__(self):
        return f"{self.exception_type} - {self.employee} on {self.exception_date}"

    def approve(self, reviewer):
        """Approve and apply corrections"""
        self.status = self.ExceptionStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        
        if self.attendance_record:
            if self.proposed_clock_in:
                self.attendance_record.clock_in = self.proposed_clock_in
            if self.proposed_clock_out:
                self.attendance_record.clock_out = self.proposed_clock_out
            if self.proposed_status:
                self.attendance_record.status = self.proposed_status
            self.attendance_record.is_manually_entered = True
            self.attendance_record.save()

    def reject(self, reviewer, comments=''):
        """Reject the exception"""
        self.status = self.ExceptionStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_comments = comments
        self.save()


class AttendancePolicy(models.Model):
    """Attendance policies for Zimbabwe compliance"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    # Policy settings
    required_work_hours_per_day = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('8.00')
    )
    required_work_days_per_week = models.PositiveIntegerField(default=5)
    required_work_hours_per_week = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('40.00')
    )
    
    # Overtime settings
    overtime_allowed = models.BooleanField(default=True)
    max_overtime_hours_per_day = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('4.00')
    )
    max_overtime_hours_per_week = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('12.00')
    )
    overtime_requires_approval = models.BooleanField(default=True)
    
    # Late arrival settings
    late_arrival_grace_period = models.PositiveIntegerField(default=15, help_text="Minutes")
    max_late_arrivals_per_month = models.PositiveIntegerField(default=3)
    late_deduction_threshold_minutes = models.PositiveIntegerField(default=30)
    
    # Absence settings
    max_unauthorized_absences_per_month = models.PositiveIntegerField(default=2)
    consecutive_absences_trigger = models.PositiveIntegerField(default=3)
    
    # Leave settings
    half_day_hours_threshold = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('4.00')
    )
    
    # Break settings
    mandatory_break_after_hours = models.DecimalField(
        max_digits=3, decimal_places=1, default=Decimal('5.0')
    )
    min_break_duration_minutes = models.PositiveIntegerField(default=30)
    
    # Remote work
    remote_work_allowed = models.BooleanField(default=False)
    requires_photo_verification = models.BooleanField(default=False)
    requires_location_tracking = models.BooleanField(default=True)
    
    # Disciplinary
    disciplinary_action_threshold = models.PositiveIntegerField(default=5)
    
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Attendance Policies'
        ordering = ['-effective_from']

    def __str__(self):
        return self.name

    @property
    def is_currently_effective(self):
        """Check if policy is currently in effect"""
        today = date.today()
        if self.effective_to:
            return self.effective_from <= today <= self.effective_to
        return self.effective_from <= today


class AttendanceSummary(models.Model):
    """Monthly attendance summary"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_summaries'
    )
    month = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.PositiveIntegerField()
    
    # Counts
    total_working_days = models.PositiveIntegerField(default=0)
    present_days = models.PositiveIntegerField(default=0)
    absent_days = models.PositiveIntegerField(default=0)
    late_days = models.PositiveIntegerField(default=0)
    half_days = models.PositiveIntegerField(default=0)
    leave_days = models.PositiveIntegerField(default=0)
    weekend_work_days = models.PositiveIntegerField(default=0)
    holiday_work_days = models.PositiveIntegerField(default=0)
    
    # Hours
    total_work_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_break_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Metrics
    total_late_minutes = models.PositiveIntegerField(default=0)
    average_work_hours_per_day = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    punctuality_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Flags
    has_disciplinary_issues = models.BooleanField(default=False)
    disciplinary_notes = models.TextField(blank=True)
    
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month']
        verbose_name = _('Attendance Summary')
        verbose_name_plural = _('Attendance Summaries')

    def __str__(self):
        return f"{self.employee} - {self.month}/{self.year}"

    @property
    def absence_rate(self):
        """Calculate absence rate percentage"""
        if self.total_working_days > 0:
            return round((self.absent_days / self.total_working_days) * 100, 2)
        return 0

    @property
    def overall_score(self):
        """Calculate overall attendance score"""
        if self.attendance_percentage == 0:
            return 0
        
        # Weighted score: 60% attendance, 40% punctuality
        return round(
            (self.attendance_percentage * 0.6) + (self.punctuality_score * 0.4), 2
        )

    def regenerate(self):
        """Regenerate summary from attendance records"""
        from django.db.models import Sum, Avg, Q
        from calendar import monthrange
        
        _, last_day = monthrange(self.year, self.month)
        start_date = date(self.year, self.month, 1)
        end_date = date(self.year, self.month, last_day)
        
        records = AttendanceRecord.objects.filter(
            employee=self.employee,
            date__range=[start_date, end_date]
        )
        
        self.total_working_days = records.exclude(status='WEEKEND').count()
        self.present_days = records.filter(
            Q(status='PRESENT') | Q(status='LATE') | Q(status='OVERTIME')
        ).count()
        self.absent_days = records.filter(status__in=['ABSENT', 'UNAUTHORIZED']).count()
        self.late_days = records.filter(is_late=True).count()
        self.half_days = records.filter(status='HALF_DAY').count()
        self.leave_days = records.filter(status__in=['ON_LEAVE', 'SICK_LEAVE']).count()
        self.weekend_work_days = records.filter(is_weekend_work=True).count()
        self.holiday_work_days = records.filter(is_public_holiday_work=True).count()
        
        total_hours = sum(r.work_hours for r in records if r.work_hours)
        self.total_work_hours = Decimal(str(total_hours))
        
        total_ot = sum(r.overtime_hours for r in records if r.overtime_hours)
        self.total_overtime_hours = Decimal(str(total_ot))
        
        self.total_break_hours = Decimal(str(
            records.aggregate(Sum('total_break_minutes'))['total_break_minutes__sum'] or 0
        )) / Decimal('60')
        
        self.total_late_minutes = records.aggregate(Sum('late_minutes'))['late_minutes__sum'] or 0
        
        if self.present_days > 0:
            self.average_work_hours_per_day = self.total_work_hours / self.present_days
            on_time_days = self.present_days - self.late_days
            self.punctuality_score = Decimal(str((on_time_days / self.present_days) * 100))
        
        if self.total_working_days > 0:
            self.attendance_percentage = Decimal(str((self.present_days / self.total_working_days) * 100))
        
        self.save()