from django.db import models
from django.core.validators import RegexValidator
from apps.core.models import TimeStampedModel, Department, Company

class JobLevel(TimeStampedModel):
    """Job levels/grades in organization"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='job_levels')
    name = models.CharField(max_length=100)  # e.g., "Junior", "Senior", "Manager"
    code = models.CharField(max_length=10)
    level_number = models.IntegerField()  # 1, 2, 3, etc.
    min_salary = models.DecimalField(max_digits=10, decimal_places=2)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['company', 'code']
        ordering = ['level_number']
    
    def __str__(self):
        return f"{self.name} (Level {self.level_number})"

class Position(TimeStampedModel):
    """Job positions"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    job_level = models.ForeignKey(JobLevel, on_delete=models.PROTECT)
    description = models.TextField()
    responsibilities = models.TextField()
    requirements = models.TextField()
    reports_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinate_positions')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['company', 'code']
    
    def __str__(self):
        return f"{self.title} - {self.department.name}"

class Employee(TimeStampedModel):
    """Comprehensive employee profile"""
    EMPLOYMENT_TYPE = [
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('probation', 'Probation'),
        ('intern', 'Intern'),
        ('casual', 'Casual'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    MARITAL_STATUS = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    
    # Basic Information
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    employee_id = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS)
    national_id = models.CharField(max_length=50)
    passport_number = models.CharField(max_length=50, blank=True)
    
    # Contact Information
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$')
    phone_number = models.CharField(validators=[phone_regex], max_length=17)
    personal_email = models.EmailField()
    work_email = models.EmailField(unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Employment Information
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name='employees')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE)
    date_joined = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    date_left = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='team_members')
    is_active = models.BooleanField(default=True)
    
    # Compensation
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_frequency = models.CharField(max_length=20, default='monthly')  # monthly, bi-weekly
    
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200)
    emergency_contact_phone = models.CharField(max_length=17)
    emergency_contact_relationship = models.CharField(max_length=50)
    emergency_contact_address = models.TextField(blank=True)
    
    # Profile
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True)
    bio = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['company', 'employee_id']
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.employee_id} - {self.get_full_name()}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def years_of_service(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_joined.year

class EmployeeSkill(TimeStampedModel):
    """Employee skills and proficiency levels"""
    PROFICIENCY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS)
    years_experience = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    certified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['employee', 'skill_name']

class EmployeeDocument(TimeStampedModel):
    """Employee document repository"""
    DOCUMENT_TYPES = [
        ('cv', 'CV/Resume'),
        ('id_copy', 'ID Copy'),
        ('passport', 'Passport Copy'),
        ('certificate', 'Educational Certificate'),
        ('contract', 'Employment Contract'),
        ('medical', 'Medical Certificate'),
        ('police_clearance', 'Police Clearance'),
        ('reference', 'Reference Letter'),
        ('other', 'Other'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='employee_documents/%Y/%m/')
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents')
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']

class EmployeeDependant(TimeStampedModel):
    """Employee dependants for benefits"""
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other', 'Other'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='dependants')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    national_id = models.CharField(max_length=50, blank=True)
    is_beneficiary = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.relationship})"
