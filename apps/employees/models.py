from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal


class Department(models.Model):
    """
    Department/Division within the organization
    """
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
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name[:3].upper()
        super().save(*args, **kwargs)

    @property
    def employee_count(self):
        """Return the number of active employees in this department"""
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
            return (self.budget_used / self.annual_budget) * 100
        return 0

    def get_all_employees(self, include_sub_departments=True):
        """Get all employees including sub-departments"""
        employees = self.employee_set.filter(status='ACTIVE')
        if include_sub_departments:
            for sub_dept in self.sub_departments.filter(is_active=True):
                employees = employees | sub_dept.get_all_employees()
        return employees.distinct()

    def get_hierarchy_level(self):
        """Get the hierarchical level of this department"""
        level = 0
        current = self.parent_department
        while current:
            level += 1
            current = current.parent_department
            if level > 10:  # Prevent infinite loops
                break
        return level


class Designation(models.Model):
    """
    Job title/position within the organization
    """
    title = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    level = models.PositiveIntegerField(
        default=1,
        help_text="Organizational level (1=Entry, 5=Executive)"
    )
    
    # Salary range
    min_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum salary for this position in USD"
    )
    max_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum salary for this position in USD"
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
    required_skills = models.TextField(
        blank=True,
        null=True,
        help_text="Comma-separated list of required skills"
    )
    
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
        """Count of active employees in this designation"""
        return self.employee_set.filter(status='ACTIVE').count()

    @property
    def salary_range_display(self):
        """Display salary range"""
        if self.min_salary and self.max_salary:
            return f"${self.min_salary:,.2f} - ${self.max_salary:,.2f}"
        return "Not specified"


class Employee(models.Model):
    """
    Employee information and employment details - Enhanced for Zimbabwe
    """
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
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="ZIMRA Tax Number"
    )
    nssa_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="National Social Security Authority Number"
    )
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
            ('Head Office', 'Head Office'),
            ('Branch Office', 'Branch Office'),
            ('Remote', 'Remote'),
            ('Hybrid', 'Hybrid'),
        ]
    )
    
    # Salary information
    current_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current gross salary in USD"
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
    
    # Additional flags
    is_remote_worker = models.BooleanField(default=False)
    is_union_member = models.BooleanField(default=False)
    has_security_clearance = models.BooleanField(default=False)
    can_approve_expenses = models.BooleanField(default=False)
    can_recruit = models.BooleanField(default=False)
    
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
    
    # Notes
    notes = models.TextField(blank=True, null=True, help_text="Internal notes about employee")
    
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
            models.Index(fields=['nssa_number']),
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
        # Auto-generate employee ID if not provided
        if not self.employee_id:
            last_employee = Employee.objects.all().order_by('id').last()
            next_id = (last_employee.id + 1) if last_employee else 1
            dept_code = self.department.code[:3] if self.department else 'GEN'
            year = timezone.now().year
            self.employee_id = f'{dept_code}{year}{next_id:04d}'
        
        # Set work email if not provided
        if not self.work_email and self.user.email:
            self.work_email = self.user.email
        
        # Auto-calculate probation end date (90 days) if not set
        if not self.probation_end_date and self.join_date:
            self.probation_end_date = self.join_date + timedelta(days=90)
        
        # Set next review date
        if not self.next_review_date and self.join_date:
            self.next_review_date = self.join_date + timedelta(days=365)
        
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Return employee's full name"""
        return self.user.get_full_name()

    @property
    def is_on_probation(self):
        """Check if employee is still on probation"""
        if self.status == 'PROBATION' and self.probation_end_date:
            return date.today() <= self.probation_end_date
        return False

    @property
    def probation_days_remaining(self):
        """Days remaining in probation period"""
        if self.is_on_probation:
            return (self.probation_end_date - date.today()).days
        return 0

    @property
    def tenure_years(self):
        """Calculate years of service"""
        if self.join_date:
            end_date = self.termination_date or date.today()
            return round((end_date - self.join_date).days / 365.25, 2)
        return 0

    @property
    def tenure_months(self):
        """Calculate months of service"""
        if self.join_date:
            end_date = self.termination_date or date.today()
            return round((end_date - self.join_date).days / 30.44, 1)
        return 0

    @property
    def is_manager(self):
        """Check if employee has subordinates"""
        return self.subordinates.exists()

    @property
    def subordinate_count(self):
        """Count of direct subordinates"""
        return self.subordinates.filter(status='ACTIVE').count()

    @property
    def is_contract_expiring_soon(self):
        """Check if contract is expiring within 30 days"""
        if self.contract_end_date:
            days_until_expiry = (self.contract_end_date - date.today()).days
            return 0 < days_until_expiry <= 30
        return False

    @property
    def days_until_contract_expiry(self):
        """Days until contract expiry"""
        if self.contract_end_date:
            return (self.contract_end_date - date.today()).days
        return None

    @property
    def is_due_for_review(self):
        """Check if employee is due for performance review"""
        if self.next_review_date:
            return date.today() >= self.next_review_date
        return False

    @property
    def age(self):
        """Get employee age from profile"""
        if hasattr(self.user, 'profile') and self.user.profile.date_of_birth:
            return self.user.profile.age
        return None

    def get_reporting_chain(self):
        """Get the full reporting chain up to top management"""
        chain = []
        current = self.manager
        while current:
            chain.append(current)
            current = current.manager
            if len(chain) > 10:  # Prevent infinite loops
                break
        return chain

    def get_all_subordinates(self, include_indirect=True):
        """Get all subordinates including indirect reports"""
        subordinates = list(self.subordinates.filter(status='ACTIVE'))
        if include_indirect:
            for subordinate in list(subordinates):
                subordinates.extend(subordinate.get_all_subordinates())
        return subordinates

    def calculate_annual_salary_cost(self):
        """Calculate total annual salary cost including benefits"""
        if self.current_salary:
            # Add 15% for benefits (NSSA, pension, etc.)
            return self.current_salary * 12 * Decimal('1.15')
        return Decimal('0')

    def is_eligible_for_promotion(self):
        """Check eligibility for promotion"""
        criteria = [
            self.status == 'ACTIVE',
            self.tenure_years >= 1,
            self.performance_rating and self.performance_rating >= Decimal('3.5'),
            not self.is_on_probation
        ]
        return all(criteria)


class EmergencyContact(models.Model):
    """
    Emergency contact information for employees
    """
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='emergency_contacts'
    )
    name = models.CharField(max_length=100)
    relationship = models.CharField(
        max_length=50,
        choices=[
            ('SPOUSE', 'Spouse'),
            ('PARENT', 'Parent'),
            ('SIBLING', 'Sibling'),
            ('CHILD', 'Child'),
            ('FRIEND', 'Friend'),
            ('RELATIVE', 'Relative'),
            ('OTHER', 'Other'),
        ]
    )
    phone_number = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    can_make_medical_decisions = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'name']
        verbose_name = _('Emergency Contact')
        verbose_name_plural = _('Emergency Contacts')

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.employee}"

    def save(self, *args, **kwargs):
        # Ensure only one primary contact per employee
        if self.is_primary:
            EmergencyContact.objects.filter(
                employee=self.employee, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class BankDetails(models.Model):
    """
    Banking information for salary payments - Zimbabwe banks
    """
    ZIMBABWE_BANKS = [
        ('CBZ', 'CBZ Bank'),
        ('CABS', 'CABS'),
        ('FBC', 'FBC Bank'),
        ('NMB', 'NMB Bank'),
        ('Stanbic', 'Stanbic Bank'),
        ('Standard Chartered', 'Standard Chartered Bank'),
        ('ZB Bank', 'ZB Bank'),
        ('BancABC', 'BancABC'),
        ('Steward Bank', 'Steward Bank'),
        ('Ecobank', 'Ecobank Zimbabwe'),
        ('First Capital Bank', 'First Capital Bank'),
        ('Nedbank', 'Nedbank Zimbabwe'),
        ('Agribank', 'Agribank'),
        ('POSB', 'People\'s Own Savings Bank'),
        ('MetBank', 'MetBank'),
    ]
    
    employee = models.OneToOneField(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='bank_details'
    )
    bank_name = models.CharField(max_length=100, choices=ZIMBABWE_BANKS)
    account_number = models.CharField(max_length=50)
    account_holder_name = models.CharField(max_length=100, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    branch_code = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(
        max_length=20,
        choices=[
            ('SAVINGS', 'Savings'),
            ('CURRENT', 'Current/Checking'),
            ('NOSTRO', 'Nostro (USD)'),
        ],
        default='SAVINGS'
    )
    swift_code = models.CharField(max_length=20, blank=True)
    
    # Mobile money options
    has_mobile_money = models.BooleanField(default=False)
    mobile_money_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('ECOCASH', 'EcoCash'),
            ('ONEMONEY', 'OneMoney'),
            ('TELECASH', 'TeleCash'),
        ]
    )
    mobile_money_number = models.CharField(max_length=20, blank=True, null=True)
    
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_bank_details'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Bank Details')
        verbose_name_plural = _('Bank Details')

    def __str__(self):
        return f"{self.employee} - {self.bank_name}"

    def save(self, *args, **kwargs):
        if not self.account_holder_name:
            self.account_holder_name = self.employee.full_name
        super().save(*args, **kwargs)


class EmployeeDocument(models.Model):
    """
    Document storage for employee records
    """
    class DocumentType(models.TextChoices):
        ID = 'ID', _('National ID')
        PASSPORT = 'PASSPORT', _('Passport')
        CERTIFICATE = 'CERTIFICATE', _('Certificate/Diploma')
        DEGREE = 'DEGREE', _('Degree')
        CONTRACT = 'CONTRACT', _('Employment Contract')
        RESUME = 'RESUME', _('Resume/CV')
        MEDICAL = 'MEDICAL', _('Medical Certificate')
        POLICE_CLEARANCE = 'POLICE_CLEARANCE', _('Police Clearance')
        TAX_CLEARANCE = 'TAX_CLEARANCE', _('Tax Clearance')
        REFERENCE = 'REFERENCE', _('Reference Letter')
        OTHER = 'OTHER', _('Other')

    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    title = models.CharField(max_length=200)
    document = models.FileField(upload_to='employee_documents/%Y/%m/')
    description = models.TextField(blank=True, null=True)
    document_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID/Passport/Certificate number"
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
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
        verbose_name = _('Employee Document')
        verbose_name_plural = _('Employee Documents')

    def __str__(self):
        return f"{self.title} - {self.employee}"

    @property
    def file_size(self):
        """Return file size in MB"""
        if self.document:
            return round(self.document.size / (1024 * 1024), 2)
        return 0

    @property
    def is_expiring_soon(self):
        """Check if document expires within 30 days"""
        if self.expiry_date:
            days_until_expiry = (self.expiry_date - date.today()).days
            return 0 < days_until_expiry <= 30
        return False

    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False


class Dependent(models.Model):
    """
    Employee dependents for benefits and tax purposes
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='dependents'
    )
    name = models.CharField(max_length=200)
    relationship = models.CharField(
        max_length=50,
        choices=[
            ('SPOUSE', 'Spouse'),
            ('CHILD', 'Child'),
            ('PARENT', 'Parent'),
            ('SIBLING', 'Sibling'),
            ('OTHER', 'Other'),
        ]
    )
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female')]
    )
    national_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Medical aid information
    is_on_medical_aid = models.BooleanField(default=False)
    medical_aid_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Education (for children)
    is_student = models.BooleanField(default=False)
    school_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Tax purposes
    is_tax_dependent = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['relationship', 'name']
        verbose_name = 'Dependent'
        verbose_name_plural = 'Dependents'

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.employee}"

    @property
    def age(self):
        """Calculate dependent's age"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class EmployeeNote(models.Model):
    """
    Internal notes and observations about employees
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='internal_notes'
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    note_type = models.CharField(
        max_length=30,
        choices=[
            ('GENERAL', 'General Note'),
            ('PERFORMANCE', 'Performance Note'),
            ('DISCIPLINARY', 'Disciplinary Note'),
            ('ACHIEVEMENT', 'Achievement'),
            ('CONCERN', 'Concern'),
            ('MEETING', 'Meeting Notes'),
        ],
        default='GENERAL'
    )
    is_confidential = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='employee_notes_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Employee Note'
        verbose_name_plural = 'Employee Notes'

    def __str__(self):
        return f"{self.title} - {self.employee}"


# Signals
@receiver(post_save, sender=Employee)
def create_employee_bank_details(sender, instance, created, **kwargs):
    """
    Create bank details record when employee is created
    """
    if created:
        BankDetails.objects.get_or_create(employee=instance)


@receiver(post_save, sender=Employee)
def update_employee_status(sender, instance, **kwargs):
    """
    Automatically update employee status based on dates
    """
    if instance.status == 'PROBATION' and instance.probation_end_date:
        if date.today() > instance.probation_end_date and not instance.confirmation_date:
            # Probation ended but not confirmed - needs review
            pass
    
    if instance.contract_end_date and date.today() > instance.contract_end_date:
        if instance.employment_type == 'CONTRACT' and instance.status == 'ACTIVE':
            # Contract expired - needs review
            pass