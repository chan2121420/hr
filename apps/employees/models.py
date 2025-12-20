from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Count, Avg
from datetime import date, timedelta
from decimal import Decimal
import uuid


class Department(models.Model):
    """Enhanced Department model with budgeting and hierarchy"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    head = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments_headed'
    )
    parent_department = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_departments'
    )
    
    # Budget information
    annual_budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual budget in USD"
    )
    budget_used = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Budget used so far"
    )
    
    # Contact information
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    
    # Cost center
    cost_center_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Goals and objectives
    objectives = models.TextField(blank=True, null=True)
    kpis = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['parent_department']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name[:3].upper()
        super().save(*args, **kwargs)

    @property
    def employee_count(self):
        """Return the number of active employees"""
        return self.employee_set.filter(status='ACTIVE').count()

    @property
    def budget_remaining(self):
        """Calculate remaining budget"""
        if self.annual_budget:
            return self.annual_budget - self.budget_used
        return None

    @property
    def budget_utilization_percentage(self):
        """Calculate budget utilization percentage"""
        if self.annual_budget and self.annual_budget > 0:
            return round((self.budget_used / self.annual_budget) * 100, 2)
        return 0

    def get_all_employees(self, include_sub_departments=True):
        """Get all employees including sub-departments"""
        from django.db.models import Q
        query = Q(department=self, status='ACTIVE')
        
        if include_sub_departments:
            sub_dept_ids = self.get_all_sub_departments()
            query |= Q(department__in=sub_dept_ids, status='ACTIVE')
        
        return Employee.objects.filter(query).distinct()

    def get_all_sub_departments(self):
        """Get all sub-department IDs recursively"""
        sub_depts = list(self.sub_departments.filter(is_active=True))
        all_subs = sub_depts.copy()
        
        for sub in sub_depts:
            all_subs.extend(sub.get_all_sub_departments())
        
        return all_subs

    def get_hierarchy_level(self):
        """Get the hierarchical level"""
        level = 0
        current = self.parent_department
        while current and level < 10:
            level += 1
            current = current.parent_department
        return level

    def get_average_salary(self):
        """Get average salary in department"""
        return self.employee_set.filter(
            status='ACTIVE',
            current_salary__isnull=False
        ).aggregate(avg=Avg('current_salary'))['avg'] or 0

    def get_total_payroll_cost(self):
        """Calculate total monthly payroll cost"""
        total = self.employee_set.filter(
            status='ACTIVE',
            current_salary__isnull=False
        ).aggregate(total=models.Sum('current_salary'))['total'] or 0
        return total


class Designation(models.Model):
    """Enhanced Job title/position"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    level = models.PositiveIntegerField(
        default=1,
        help_text="Organizational level (1=Entry, 5=Executive)"
    )
    
    # Career progression
    next_level_designation = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_level_designations'
    )
    
    # Salary range
    min_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum salary in USD"
    )
    max_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum salary in USD"
    )
    
    # Reporting structure
    reports_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinate_positions'
    )
    
    # Job requirements
    required_education = models.TextField(blank=True, null=True)
    required_experience_years = models.PositiveIntegerField(default=0)
    required_skills = models.JSONField(default=list, blank=True)
    required_certifications = models.JSONField(default=list, blank=True)
    
    # Responsibilities
    key_responsibilities = models.JSONField(default=list, blank=True)
    
    # Benefits
    eligible_for_bonus = models.BooleanField(default=True)
    eligible_for_overtime = models.BooleanField(default=False)
    eligible_for_company_car = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level', 'title']
        verbose_name = _('Designation')
        verbose_name_plural = _('Designations')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join([word[0] for word in self.title.split()[:3]]).upper()
        super().save(*args, **kwargs)

    @property
    def current_employee_count(self):
        """Count of active employees"""
        return self.employee_set.filter(status='ACTIVE').count()

    @property
    def salary_range_display(self):
        """Display salary range"""
        if self.min_salary and self.max_salary:
            return f"${self.min_salary:,.2f} - ${self.max_salary:,.2f}"
        return "Not specified"


class Employee(models.Model):
    """Enhanced Employee model for Zimbabwe"""
    
    class EmploymentStatus(models.TextChoices):
        PROBATION = 'PROBATION', _('Probation')
        ACTIVE = 'ACTIVE', _('Active')
        ON_LEAVE = 'ON_LEAVE', _('On Leave')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        TERMINATED = 'TERMINATED', _('Terminated')
        RESIGNED = 'RESIGNED', _('Resigned')
        RETIRED = 'RETIRED', _('Retired')
        DECEASED = 'DECEASED', _('Deceased')

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', _('Full-Time')
        PART_TIME = 'PART_TIME', _('Part-Time')
        CONTRACT = 'CONTRACT', _('Contract')
        INTERN = 'INTERN', _('Intern')
        CONSULTANT = 'CONSULTANT', _('Consultant')
        TEMPORARY = 'TEMPORARY', _('Temporary')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    employee_id = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    shift = models.ForeignKey(
        'attendance.Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    
    # Employment dates
    join_date = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)
    confirmation_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    last_promotion_date = models.DateField(null=True, blank=True)
    
    # Employment details
    status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.PROBATION,
        db_index=True
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME
    )
    
    # Zimbabwe-specific fields
    work_email = models.EmailField(blank=True, null=True)
    work_phone = models.CharField(max_length=20, blank=True, null=True)
    national_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True, help_text="ZIMRA Tax Number")
    nssa_number = models.CharField(max_length=50, blank=True, null=True, help_text="NSSA Number")
    pension_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Contract details
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    contract_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('FIXED_TERM', 'Fixed Term'),
            ('INDEFINITE', 'Indefinite'),
            ('PROJECT_BASED', 'Project Based'),
        ]
    )
    
    # Work location
    work_location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        choices=[
            ('HEAD_OFFICE', 'Head Office'),
            ('BRANCH', 'Branch Office'),
            ('REMOTE', 'Remote'),
            ('HYBRID', 'Hybrid'),
        ]
    )
    office_location = models.CharField(max_length=200, blank=True, null=True)
    
    # Salary information
    current_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current gross salary"
    )
    salary_currency = models.CharField(
        max_length=3,
        default='USD',
        choices=[('USD', 'US Dollar'), ('ZWL', 'Zimbabwe Dollar')]
    )
    
    # Performance
    performance_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Last performance rating (out of 5)"
    )
    last_review_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    
    # Skills and competencies
    skills = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    
    # Additional flags
    is_remote_worker = models.BooleanField(default=False)
    is_union_member = models.BooleanField(default=False)
    has_security_clearance = models.BooleanField(default=False)
    can_approve_expenses = models.BooleanField(default=False)
    can_recruit = models.BooleanField(default=False)
    can_approve_leave = models.BooleanField(default=False)
    can_approve_timesheets = models.BooleanField(default=False)
    
    # Emergency contact stored as JSON for flexibility
    emergency_contact_info = models.JSONField(default=dict, blank=True)
    
    # Termination details
    termination_reason = models.TextField(blank=True, null=True)
    termination_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('VOLUNTARY', 'Voluntary Resignation'),
            ('INVOLUNTARY', 'Involuntary Termination'),
            ('RETIREMENT', 'Retirement'),
            ('CONTRACT_END', 'Contract End'),
            ('MUTUAL', 'Mutual Agreement'),
        ]
    )
    eligible_for_rehire = models.BooleanField(default=True)
    exit_interview_completed = models.BooleanField(default=False)
    exit_interview_date = models.DateField(null=True, blank=True)
    final_settlement_date = models.DateField(null=True, blank=True)
    
    # Onboarding
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completion_date = models.DateField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='employees_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-join_date']
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
        indexes = [
            models.Index(fields=['employee_id', 'status']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['national_id']),
            models.Index(fields=['work_email']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    def clean(self):
        """Validate employee data"""
        if self.termination_date and self.join_date:
            if self.termination_date < self.join_date:
                raise ValidationError('Termination date cannot be before join date')
        
        if self.manager == self:
            raise ValidationError('An employee cannot be their own manager')
        
        if self.contract_end_date and self.contract_start_date:
            if self.contract_end_date < self.contract_start_date:
                raise ValidationError('Contract end date cannot be before start date')

    def save(self, *args, **kwargs):
        # Auto-generate employee ID
        if not self.employee_id:
            last_employee = Employee.objects.all().order_by('-created_at').first()
            next_id = 1
            if last_employee and last_employee.employee_id:
                try:
                    last_num = int(last_employee.employee_id.split('-')[-1])
                    next_id = last_num + 1
                except:
                    pass
            
            dept_code = self.department.code[:3] if self.department else 'GEN'
            year = timezone.now().year % 100
            self.employee_id = f'{dept_code}-{year:02d}-{next_id:05d}'
        
        # Set work email
        if not self.work_email and self.user.email:
            self.work_email = self.user.email
        
        # Auto-calculate probation end date
        if not self.probation_end_date and self.join_date:
            self.probation_end_date = self.join_date + timedelta(days=90)
        
        # Set next review date
        if not self.next_review_date and self.join_date:
            self.next_review_date = self.join_date + timedelta(days=365)
        
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def is_on_probation(self):
        if self.status == 'PROBATION' and self.probation_end_date:
            return date.today() <= self.probation_end_date
        return False

    @property
    def probation_days_remaining(self):
        if self.is_on_probation:
            return (self.probation_end_date - date.today()).days
        return 0

    @property
    def tenure_years(self):
        if self.join_date:
            end_date = self.termination_date or date.today()
            return round((end_date - self.join_date).days / 365.25, 2)
        return 0

    @property
    def tenure_months(self):
        if self.join_date:
            end_date = self.termination_date or date.today()
            return round((end_date - self.join_date).days / 30.44, 1)
        return 0

    @property
    def is_manager(self):
        return self.subordinates.filter(status='ACTIVE').exists()

    @property
    def subordinate_count(self):
        return self.subordinates.filter(status='ACTIVE').count()

    @property
    def is_contract_expiring_soon(self):
        if self.contract_end_date:
            days_until = (self.contract_end_date - date.today()).days
            return 0 < days_until <= 30
        return False

    @property
    def days_until_contract_expiry(self):
        if self.contract_end_date:
            return (self.contract_end_date - date.today()).days
        return None

    @property
    def is_due_for_review(self):
        if self.next_review_date:
            return date.today() >= self.next_review_date
        return False

    def get_reporting_chain(self):
        """Get full reporting chain"""
        chain = []
        current = self.manager
        while current and len(chain) < 10:
            chain.append(current)
            current = current.manager
        return chain

    def get_all_subordinates(self, include_indirect=True):
        """Get all subordinates including indirect"""
        subordinates = list(self.subordinates.filter(status='ACTIVE'))
        if include_indirect:
            for sub in list(subordinates):
                subordinates.extend(sub.get_all_subordinates())
        return list(set(subordinates))

    def calculate_annual_cost(self):
        """Calculate total annual cost"""
        if self.current_salary:
            return self.current_salary * 12 * Decimal('1.15')
        return Decimal('0')


class EmergencyContact(models.Model):
    """Emergency contact information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50, choices=[
        ('SPOUSE', 'Spouse'), ('PARENT', 'Parent'), ('SIBLING', 'Sibling'),
        ('CHILD', 'Child'), ('FRIEND', 'Friend'), ('RELATIVE', 'Relative'), ('OTHER', 'Other'),
    ])
    phone_number = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    can_make_medical_decisions = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.name} ({self.relationship})"

    def save(self, *args, **kwargs):
        if self.is_primary:
            EmergencyContact.objects.filter(
                employee=self.employee,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class BankDetails(models.Model):
    """Banking information for Zimbabwe"""
    ZIMBABWE_BANKS = [
        ('CBZ', 'CBZ Bank'), ('CABS', 'CABS'), ('FBC', 'FBC Bank'),
        ('NMB', 'NMB Bank'), ('Stanbic', 'Stanbic Bank'),
        ('Standard Chartered', 'Standard Chartered'), ('ZB Bank', 'ZB Bank'),
        ('BancABC', 'BancABC'), ('Steward Bank', 'Steward Bank'),
        ('Ecobank', 'Ecobank'), ('First Capital Bank', 'First Capital Bank'),
        ('Nedbank', 'Nedbank'), ('Agribank', 'Agribank'),
        ('POSB', 'POSB'), ('MetBank', 'MetBank'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='bank_details')
    bank_name = models.CharField(max_length=100, choices=ZIMBABWE_BANKS)
    account_number = models.CharField(max_length=50)
    account_holder_name = models.CharField(max_length=100, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    branch_code = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(max_length=20, choices=[
        ('SAVINGS', 'Savings'), ('CURRENT', 'Current'), ('NOSTRO', 'Nostro (USD)'),
    ], default='SAVINGS')
    swift_code = models.CharField(max_length=20, blank=True)
    
    # Mobile money
    has_mobile_money = models.BooleanField(default=False)
    mobile_money_provider = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('ECOCASH', 'EcoCash'), ('ONEMONEY', 'OneMoney'), ('TELECASH', 'TeleCash'),
    ])
    mobile_money_number = models.CharField(max_length=20, blank=True, null=True)
    
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.bank_name}"


class EmployeeDocument(models.Model):
    """Document storage"""
    class DocumentType(models.TextChoices):
        ID = 'ID', _('National ID')
        PASSPORT = 'PASSPORT', _('Passport')
        CERTIFICATE = 'CERTIFICATE', _('Certificate')
        DEGREE = 'DEGREE', _('Degree')
        CONTRACT = 'CONTRACT', _('Contract')
        RESUME = 'RESUME', _('Resume')
        MEDICAL = 'MEDICAL', _('Medical Certificate')
        POLICE_CLEARANCE = 'POLICE_CLEARANCE', _('Police Clearance')
        TAX_CLEARANCE = 'TAX_CLEARANCE', _('Tax Clearance')
        REFERENCE = 'REFERENCE', _('Reference')
        OTHER = 'OTHER', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    title = models.CharField(max_length=200)
    document = models.FileField(upload_to='employee_documents/%Y/%m/')
    description = models.TextField(blank=True, null=True)
    document_number = models.CharField(max_length=100, blank=True, null=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    is_confidential = models.BooleanField(default=False)
    is_mandatory = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.employee}"

    @property
    def is_expiring_soon(self):
        if self.expiry_date:
            return 0 < (self.expiry_date - date.today()).days <= 30
        return False

    @property
    def is_expired(self):
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False


class Dependent(models.Model):
    """Employee dependents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='dependents')
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50, choices=[
        ('SPOUSE', 'Spouse'), ('CHILD', 'Child'), ('PARENT', 'Parent'),
        ('SIBLING', 'Sibling'), ('OTHER', 'Other'),
    ])
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')])
    national_id = models.CharField(max_length=50, blank=True, null=True)
    is_on_medical_aid = models.BooleanField(default=False)
    medical_aid_number = models.CharField(max_length=50, blank=True, null=True)
    is_student = models.BooleanField(default=False)
    school_name = models.CharField(max_length=200, blank=True, null=True)
    is_tax_dependent = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class EmployeeNote(models.Model):
    """Internal employee notes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='internal_notes')
    title = models.CharField(max_length=200)
    content = models.TextField()
    note_type = models.CharField(max_length=30, choices=[
        ('GENERAL', 'General'), ('PERFORMANCE', 'Performance'),
        ('DISCIPLINARY', 'Disciplinary'), ('ACHIEVEMENT', 'Achievement'),
        ('CONCERN', 'Concern'), ('MEETING', 'Meeting Notes'),
    ], default='GENERAL')
    is_confidential = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.employee}"