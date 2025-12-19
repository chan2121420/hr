from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from apps.employees.models import Employee
from datetime import datetime, timedelta, time, date
from decimal import Decimal


class Shift(models.Model):
    """
    Work shift definitions with Zimbabwe-specific considerations
    """
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
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'

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

    def is_working_day(self, date_obj):
        """Check if given date is a working day for this shift"""
        day_map = {
            0: self.monday,
            1: self.tuesday,
            2: self.wednesday,
            3: self.thursday,
            4: self.friday,
            5: self.saturday,
            6: self.sunday,
        }
        return day_map.get(date_obj.weekday(), False)


class AttendanceRecord(models.Model):
    """
    Daily attendance records for employees with comprehensive tracking
    """
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        ON_LEAVE = 'ON_LEAVE', 'On Leave'
        HOLIDAY = 'HOLIDAY', 'Holiday'
        LATE = 'LATE', 'Late'
        HALF_DAY = 'HALF_DAY', 'Half Day'
        PENDING = 'PENDING', 'Pending'
        WEEKEND = 'WEEKEND', 'Weekend'
        OVERTIME = 'OVERTIME', 'Overtime'
        SICK_LEAVE = 'SICK_LEAVE', 'Sick Leave'
        UNAUTHORIZED = 'UNAUTHORIZED', 'Unauthorized Absence'

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
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    clock_in_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    clock_out_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    clock_out_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # IP and device tracking
    clock_in_ip = models.GenericIPAddressField(null=True, blank=True)
    clock_out_ip = models.GenericIPAddressField(null=True, blank=True)
    clock_in_device = models.CharField(max_length=200, blank=True)
    clock_out_device = models.CharField(max_length=200, blank=True)
    
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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date', 'employee']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
            models.Index(fields=['shift', 'date']),
        ]

    def __str__(self):
        return f"{self.employee} on {self.date} ({self.status})"

    def clean(self):
        """Validate attendance record"""
        if self.clock_out and self.clock_in:
            if self.clock_out <= self.clock_in:
                raise ValidationError('Clock out time must be after clock in time')

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
            
            # Handle night shifts
            if self.shift.is_night_shift:
                scheduled_end += timedelta(days=1)
            
            grace_period = timedelta(minutes=self.shift.early_departure_grace_minutes)
            if self.clock_out < scheduled_end - grace_period:
                self.is_early_departure = True
                self.early_departure_minutes = int(
                    (scheduled_end - self.clock_out).total_seconds() / 60
                )
        
        # Update status if both clock in and clock out are recorded
        if self.clock_in and self.clock_out and self.status == 'PENDING':
            self.status = 'PRESENT'
        
        # Check if weekend work
        if self.date.weekday() >= 5:  # Saturday or Sunday
            self.is_weekend_work = True
        
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
        multiplier = Decimal('1.5')  # Default
        
        if self.shift:
            multiplier = self.shift.overtime_multiplier
        
        # Weekend work gets higher multiplier
        if self.is_weekend_work:
            multiplier = Decimal('2.0')
        
        # Public holiday work gets even higher multiplier
        if self.is_public_holiday_work:
            multiplier = Decimal('2.5')
        
        return multiplier

    @property
    def efficiency_score(self):
        """Calculate work efficiency score (productive hours / work hours)"""
        if self.work_hours > 0 and self.productive_hours:
            return round((float(self.productive_hours) / self.work_hours) * 100, 2)
        return 0

    def calculate_pay(self, hourly_rate):
        """Calculate total pay for this attendance record"""
        if not hourly_rate:
            return Decimal('0')
        
        regular_pay = Decimal(str(self.work_hours)) * hourly_rate
        overtime_pay = Decimal(str(self.overtime_hours)) * hourly_rate * self.overtime_pay_multiplier
        
        return regular_pay + overtime_pay


class AttendanceBreak(models.Model):
    """
    Track individual break periods within attendance records
    """
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
            ('OTHER', 'Other'),
        ],
        default='LUNCH'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['break_start']
        verbose_name = 'Attendance Break'
        verbose_name_plural = 'Attendance Breaks'

    def __str__(self):
        return f"{self.break_type} - {self.attendance_record}"

    @property
    def duration_minutes(self):
        """Calculate break duration in minutes"""
        if self.break_start and self.break_end:
            duration = self.break_end - self.break_start
            return int(duration.total_seconds() / 60)
        return 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update total break time in attendance record
        if self.attendance_record and self.break_end:
            total_break = sum(
                b.duration_minutes for b in 
                self.attendance_record.breaks.filter(break_end__isnull=False)
            )
            self.attendance_record.total_break_minutes = total_break
            self.attendance_record.save(update_fields=['total_break_minutes'])


class AttendanceException(models.Model):
    """
    Track attendance exceptions and requests for corrections
    """
    class ExceptionType(models.TextChoices):
        FORGOT_CLOCK_IN = 'FORGOT_CLOCK_IN', 'Forgot to Clock In'
        FORGOT_CLOCK_OUT = 'FORGOT_CLOCK_OUT', 'Forgot to Clock Out'
        LATE_ARRIVAL = 'LATE_ARRIVAL', 'Late Arrival'
        EARLY_DEPARTURE = 'EARLY_DEPARTURE', 'Early Departure'
        MISSED_DAY = 'MISSED_DAY', 'Missed Day'
        SYSTEM_ERROR = 'SYSTEM_ERROR', 'System Error'
        DEVICE_ISSUE = 'DEVICE_ISSUE', 'Device Issue'
        OTHER = 'OTHER', 'Other'

    class ExceptionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

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
    
    # Priority flag
    is_urgent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Attendance Exception'
        verbose_name_plural = 'Attendance Exceptions'

    def __str__(self):
        return f"{self.exception_type} - {self.employee} on {self.exception_date}"

    def approve(self, reviewer):
        """Approve the exception and apply corrections"""
        self.status = self.ExceptionStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        
        # Apply corrections to attendance record
        if self.attendance_record:
            if self.proposed_clock_in:
                self.attendance_record.clock_in = self.proposed_clock_in
            if self.proposed_clock_out:
                self.attendance_record.clock_out = self.proposed_clock_out
            if self.proposed_status:
                self.attendance_record.status = self.proposed_status
            self.attendance_record.save()

    def reject(self, reviewer, comments=''):
        """Reject the exception"""
        self.status = self.ExceptionStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_comments = comments
        self.save()


class AttendancePolicy(models.Model):
    """
    Attendance policies and rules for Zimbabwe compliance
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    # Policy settings
    required_work_hours_per_day = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('8.00')
    )
    required_work_days_per_week = models.PositiveIntegerField(default=5)
    required_work_hours_per_week = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('40.00')
    )
    
    # Overtime settings
    overtime_allowed = models.BooleanField(default=True)
    max_overtime_hours_per_day = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('4.00')
    )
    max_overtime_hours_per_week = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('12.00')
    )
    overtime_requires_approval = models.BooleanField(default=True)
    
    # Late arrival settings
    late_arrival_grace_period = models.PositiveIntegerField(
        default=15,
        help_text="Minutes"
    )
    max_late_arrivals_per_month = models.PositiveIntegerField(default=3)
    late_deduction_threshold_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minutes late before deduction applies"
    )
    
    # Absence settings
    max_unauthorized_absences_per_month = models.PositiveIntegerField(default=2)
    consecutive_absences_trigger = models.PositiveIntegerField(
        default=3,
        help_text="Days of consecutive absence that triggers alert"
    )
    
    # Leave settings
    half_day_hours_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('4.00')
    )
    
    # Break settings
    mandatory_break_after_hours = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal('5.0'),
        help_text="Hours worked before mandatory break"
    )
    min_break_duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minimum break duration"
    )
    
    # Remote work settings
    remote_work_allowed = models.BooleanField(default=False)
    requires_photo_verification = models.BooleanField(default=False)
    requires_location_tracking = models.BooleanField(default=True)
    
    # Disciplinary
    disciplinary_action_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Number of violations before disciplinary action"
    )
    
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
    """
    Monthly attendance summary for quick reporting
    """
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
    average_work_hours_per_day = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Flags
    has_disciplinary_issues = models.BooleanField(default=False)
    disciplinary_notes = models.TextField(blank=True)
    
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month']
        verbose_name = 'Attendance Summary'
        verbose_name_plural = 'Attendance Summaries'

    def __str__(self):
        return f"{self.employee} - {self.month}/{self.year}"

    @property
    def absence_rate(self):
        """Calculate absence rate percentage"""
        if self.total_working_days > 0:
            return round((self.absent_days / self.total_working_days) * 100, 2)
        return 0

    @property
    def punctuality_score(self):
        """Calculate punctuality score (0-100)"""
        if self.present_days == 0:
            return 0
        on_time_days = self.present_days - self.late_days
        return round((on_time_days / self.present_days) * 100, 2)

    def regenerate(self):
        """Regenerate summary from attendance records"""
        from django.db.models import Sum, Avg, Q
        from calendar import monthrange
        
        # Get date range for the month
        _, last_day = monthrange(self.year, self.month)
        start_date = date(self.year, self.month, 1)
        end_date = date(self.year, self.month, last_day)
        
        # Get all attendance records for this month
        records = AttendanceRecord.objects.filter(
            employee=self.employee,
            date__range=[start_date, end_date]
        )
        
        # Calculate counts
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
        
        # Calculate hours
        total_hours = sum(r.work_hours for r in records if r.work_hours)
        self.total_work_hours = Decimal(str(total_hours))
        
        total_ot = sum(r.overtime_hours for r in records if r.overtime_hours)
        self.total_overtime_hours = Decimal(str(total_ot))
        
        self.total_break_hours = Decimal(str(
            records.aggregate(Sum('total_break_minutes'))['total_break_minutes__sum'] or 0
        )) / Decimal('60')
        
        # Calculate metrics
        self.total_late_minutes = records.aggregate(Sum('late_minutes'))['late_minutes__sum'] or 0
        
        if self.present_days > 0:
            self.average_work_hours_per_day = self.total_work_hours / self.present_days
        
        if self.total_working_days > 0:
            self.attendance_percentage = (self.present_days / self.total_working_days) * 100
        
        self.save()