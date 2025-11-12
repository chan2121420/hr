from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from apps.core.models import TimeStampedModel

class User(AbstractUser):
    """Extended user model"""
    ROLE_CHOICES = [
        ('superadmin', 'Super Administrator'),
        ('admin', 'Company Administrator'),
        ('hr_manager', 'HR Manager'),
        ('hr_officer', 'HR Officer'),
        ('dept_manager', 'Department Manager'),
        ('team_lead', 'Team Lead'),
        ('employee', 'Employee'),
    ]
    
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='users',
        null=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_account'
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)  # Pillow required
    is_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    force_password_change = models.BooleanField(default=False)

    # Override groups and permissions to avoid clashes
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',  # unique related_name
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',  # unique related_name
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        permissions = [
            ('view_all_employees', 'Can view all employees'),
            ('approve_leave', 'Can approve leave requests'),
            ('process_payroll', 'Can process payroll'),
            ('manage_tasks', 'Can manage task allocation'),
            ('view_analytics', 'Can view analytics dashboard'),
            ('manage_performance', 'Can manage performance reviews'),
        ]

class UserSession(TimeStampedModel):
    """Track user sessions for security"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()

class AuditLog(TimeStampedModel):
    """Audit trail for all system activities"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50)  # CREATE, UPDATE, DELETE, VIEW, APPROVE, etc.
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    details = models.JSONField()
    ip_address = models.GenericIPAddressField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]