from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class SystemConfiguration(models.Model):
    """
    System-wide configuration settings
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('STRING', 'String'),
            ('INTEGER', 'Integer'),
            ('FLOAT', 'Float'),
            ('BOOLEAN', 'Boolean'),
            ('JSON', 'JSON'),
        ],
        default='STRING'
    )
    category = models.CharField(
        max_length=50,
        choices=[
            ('GENERAL', 'General'),
            ('EMAIL', 'Email'),
            ('PAYROLL', 'Payroll'),
            ('ATTENDANCE', 'Attendance'),
            ('LEAVE', 'Leave'),
            ('SECURITY', 'Security'),
        ],
        default='GENERAL'
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System settings cannot be modified through UI"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'

    def __str__(self):
        return f"{self.key}: {self.value}"


class AuditLog(models.Model):
    """
    Comprehensive audit logging for all system activities
    """
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        VIEW = 'VIEW', 'View'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        APPROVE = 'APPROVE', 'Approve'
        REJECT = 'REJECT', 'Reject'
        EXPORT = 'EXPORT', 'Export'
        IMPORT = 'IMPORT', 'Import'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_representation = models.CharField(max_length=500, blank=True)
    
    # Changes tracking
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dictionary of field changes {field: {old: value, new: value}}"
    )
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    
    # Additional context
    description = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action_type', 'timestamp']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.user} - {self.action_type} {self.model_name} at {self.timestamp}"


class CompanyInfo(models.Model):
    """
    Company information for Zimbabwe
    """
    name = models.CharField(max_length=200)
    trading_name = models.CharField(max_length=200, blank=True)
    registration_number = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=100, help_text="ZIMRA Tax Number")
    nssa_number = models.CharField(max_length=100, help_text="NSSA Registration Number")
    
    # Contact information
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    
    # Physical address
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    suburb = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Zimbabwe')
    
    # Postal address
    postal_address = models.TextField(blank=True)
    
    # Banking details
    bank_name = models.CharField(max_length=100)
    bank_account_number = models.CharField(max_length=50)
    bank_branch = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    
    # Logo and branding
    logo = models.ImageField(upload_to='company/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    secondary_color = models.CharField(max_length=7, default='#10B981')
    
    # Settings
    financial_year_end = models.DateField(help_text="Financial year end date")
    default_currency = models.CharField(
        max_length=3,
        default='USD',
        choices=[('USD', 'US Dollar'), ('ZWL', 'Zimbabwe Dollar')]
    )
    
    # Statutory rates
    current_nssa_employee_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)
    current_nssa_employer_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)
    aids_levy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company Information'
        verbose_name_plural = 'Company Information'

    def __str__(self):
        return self.name


class EmailTemplate(models.Model):
    """
    Email templates for automated communications
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    subject = models.CharField(max_length=500)
    body_html = models.TextField()
    body_text = models.TextField(blank=True)
    
    category = models.CharField(
        max_length=50,
        choices=[
            ('LEAVE', 'Leave Management'),
            ('ATTENDANCE', 'Attendance'),
            ('PAYROLL', 'Payroll'),
            ('RECRUITMENT', 'Recruitment'),
            ('PERFORMANCE', 'Performance'),
            ('TRAINING', 'Training'),
            ('GENERAL', 'General'),
        ]
    )
    
    # Available variables
    available_variables = models.JSONField(
        default=list,
        help_text="List of variables that can be used in template"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Document(models.Model):
    """
    Centralized document management
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/%Y/%m/')
    
    document_type = models.CharField(
        max_length=50,
        choices=[
            ('POLICY', 'Policy'),
            ('PROCEDURE', 'Procedure'),
            ('FORM', 'Form'),
            ('HANDBOOK', 'Handbook'),
            ('REPORT', 'Report'),
            ('CERTIFICATE', 'Certificate'),
            ('OTHER', 'Other'),
        ]
    )
    
    category = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=20, default='1.0')
    
    # Access control
    is_public = models.BooleanField(default=False)
    departments = models.ManyToManyField(
        'employees.Department',
        blank=True,
        help_text="Departments with access to this document"
    )
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Document lifecycle
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True)
    
    download_count = models.PositiveIntegerField(default=0)
    
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class Announcement(models.Model):
    """
    Company-wide announcements
    """
    class AnnouncementPriority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=AnnouncementPriority.choices,
        default=AnnouncementPriority.NORMAL
    )
    
    # Targeting
    is_company_wide = models.BooleanField(default=True)
    departments = models.ManyToManyField(
        'employees.Department',
        blank=True
    )
    specific_employees = models.ManyToManyField(
        'employees.Employee',
        blank=True
    )
    
    # Schedule
    publish_date = models.DateTimeField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Acknowledgment
    requires_acknowledgment = models.BooleanField(default=False)
    acknowledged_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='acknowledged_announcements'
    )
    
    # Attachments
    attachment = models.FileField(upload_to='announcements/', blank=True, null=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-publish_date']

    def __str__(self):
        return self.title


class ActivityLog(models.Model):
    """
    Track user activity within the system
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    action = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Related object (generic foreign key)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"


class Report(models.Model):
    """
    Generated reports storage
    """
    class ReportType(models.TextChoices):
        PAYROLL = 'PAYROLL', 'Payroll Report'
        ATTENDANCE = 'ATTENDANCE', 'Attendance Report'
        LEAVE = 'LEAVE', 'Leave Report'
        EMPLOYEE = 'EMPLOYEE', 'Employee Report'
        PERFORMANCE = 'PERFORMANCE', 'Performance Report'
        ASSET = 'ASSET', 'Asset Report'
        CUSTOM = 'CUSTOM', 'Custom Report'

    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    description = models.TextField(blank=True)
    
    # Parameters used to generate report
    parameters = models.JSONField(default=dict)
    
    # File
    file = models.FileField(upload_to='reports/%Y/%m/')
    file_format = models.CharField(
        max_length=10,
        choices=[
            ('PDF', 'PDF'),
            ('EXCEL', 'Excel'),
            ('CSV', 'CSV'),
        ]
    )
    
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Report period
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    
    download_count = models.PositiveIntegerField(default=0)
    
    # Automatic cleanup
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Report will be automatically deleted after this date"
    )

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.name} - {self.generated_at.date()}"


class SystemHealth(models.Model):
    """
    System health monitoring
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Database metrics
    total_users = models.PositiveIntegerField(default=0)
    active_employees = models.PositiveIntegerField(default=0)
    pending_leaves = models.PositiveIntegerField(default=0)
    pending_attendance_exceptions = models.PositiveIntegerField(default=0)
    
    # System metrics
    disk_usage_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    database_size_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Performance metrics
    average_response_time_ms = models.PositiveIntegerField(default=0)
    error_count_24h = models.PositiveIntegerField(default=0)
    
    # Additional metrics
    metrics = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Health'
        verbose_name_plural = 'System Health Records'

    def __str__(self):
        return f"System Health - {self.timestamp}"