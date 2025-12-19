from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
import uuid


class Role(models.Model):
    """
    Role model for user permissions and access control
    """
    ROLE_TYPES = [
        ('SUPER_ADMIN', 'Super Administrator'),
        ('HR_ADMIN', 'HR Administrator'),
        ('HR_MANAGER', 'HR Manager'),
        ('DEPARTMENT_HEAD', 'Department Head'),
        ('MANAGER', 'Manager'),
        ('EMPLOYEE', 'Employee'),
        ('PAYROLL_ADMIN', 'Payroll Administrator'),
        ('RECRUITMENT', 'Recruitment Officer'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    role_type = models.CharField(max_length=30, choices=ROLE_TYPES, default='EMPLOYEE')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    # Permission flags
    can_manage_employees = models.BooleanField(default=False)
    can_approve_leaves = models.BooleanField(default=False)
    can_manage_payroll = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_recruitment = models.BooleanField(default=False)
    can_manage_attendance = models.BooleanField(default=False)
    can_manage_assets = models.BooleanField(default=False)
    can_manage_training = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join([word[0] for word in self.name.split()[:3]]).upper()
        super().save(*args, **kwargs)


class CustomUserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password
        """
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)

    def active_users(self):
        """Return only active users"""
        return self.filter(is_active=True)

    def verified_users(self):
        """Return only verified users"""
        return self.filter(is_email_verified=True, is_active=True)


class CustomUser(AbstractUser):
    """
    Custom user model with email as the primary identifier
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    role = models.ForeignKey(
        Role, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users'
    )
    
    # Email verification
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Security
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    force_password_change = models.BooleanField(default=False)
    
    # Two-factor authentication
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    
    # Session management
    session_token = models.CharField(max_length=100, blank=True, null=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    theme = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')],
        default='light'
    )
    receive_email_notifications = models.BooleanField(default=True)
    receive_sms_notifications = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    class Meta:
        ordering = ['-date_joined']
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email', 'is_active']),
            models.Index(fields=['email_verification_token']),
            models.Index(fields=['session_token']),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between
        """
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()

    def get_short_name(self):
        """
        Return the short name for the user
        """
        return self.first_name

    @property
    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False

    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration"""
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])

    def unlock_account(self):
        """Unlock account"""
        self.account_locked_until = None
        self.login_attempts = 0
        self.save(update_fields=['account_locked_until', 'login_attempts'])

    def increment_login_attempts(self):
        """Increment failed login attempts"""
        self.login_attempts += 1
        if self.login_attempts >= 5:
            self.lock_account()
        self.save(update_fields=['login_attempts'])

    def reset_login_attempts(self):
        """Reset login attempts after successful login"""
        self.login_attempts = 0
        self.save(update_fields=['login_attempts'])

    def generate_email_verification_token(self):
        """Generate email verification token"""
        self.email_verification_token = uuid.uuid4().hex
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return self.email_verification_token

    def verify_email(self, token):
        """Verify email with token"""
        if self.email_verification_token == token:
            self.is_email_verified = True
            self.email_verification_token = None
            self.save(update_fields=['is_email_verified', 'email_verification_token'])
            return True
        return False

    def has_permission(self, permission_name):
        """Check if user has specific permission through role"""
        if self.is_superuser:
            return True
        if self.role:
            return getattr(self.role, permission_name, False)
        return False

    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class Profile(models.Model):
    """
    Extended user profile information with Zimbabwe-specific fields
    """
    ZIM_PHONE_REGEX = RegexValidator(
        regex=r'^\+263[0-9]{9}$|^0[0-9]{9}$',
        message="Phone number must be in format: '+263771234567' or '0771234567'"
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/', 
        null=True, 
        blank=True, 
        default='avatars/default.png'
    )
    phone_number = models.CharField(
        validators=[ZIM_PHONE_REGEX], 
        max_length=17, 
        blank=True, 
        null=True
    )
    alternate_phone = models.CharField(
        validators=[ZIM_PHONE_REGEX],
        max_length=17,
        blank=True,
        null=True
    )
    bio = models.TextField(blank=True, null=True, max_length=500)
    
    # Zimbabwe-specific identification
    national_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="Zimbabwe National ID Number (e.g., 63-123456A63)"
    )
    passport_number = models.CharField(max_length=20, blank=True, null=True)
    tax_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="ZIMRA Tax Number"
    )
    
    # Address information
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    suburb = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=[
            ('Harare', 'Harare'),
            ('Bulawayo', 'Bulawayo'),
            ('Mutare', 'Mutare'),
            ('Gweru', 'Gweru'),
            ('Kwekwe', 'Kwekwe'),
            ('Kadoma', 'Kadoma'),
            ('Masvingo', 'Masvingo'),
            ('Chinhoyi', 'Chinhoyi'),
            ('Marondera', 'Marondera'),
            ('Norton', 'Norton'),
            ('Chegutu', 'Chegutu'),
            ('Bindura', 'Bindura'),
            ('Beitbridge', 'Beitbridge'),
            ('Redcliff', 'Redcliff'),
            ('Victoria Falls', 'Victoria Falls'),
            ('Hwange', 'Hwange'),
            ('Rusape', 'Rusape'),
            ('Chiredzi', 'Chiredzi'),
            ('Kariba', 'Kariba'),
            ('Karoi', 'Karoi'),
        ]
    )
    province = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=[
            ('Harare', 'Harare'),
            ('Bulawayo', 'Bulawayo'),
            ('Manicaland', 'Manicaland'),
            ('Mashonaland Central', 'Mashonaland Central'),
            ('Mashonaland East', 'Mashonaland East'),
            ('Mashonaland West', 'Mashonaland West'),
            ('Masvingo', 'Masvingo'),
            ('Matabeleland North', 'Matabeleland North'),
            ('Matabeleland South', 'Matabeleland South'),
            ('Midlands', 'Midlands'),
        ]
    )
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='Zimbabwe')
    
    # Personal information
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        blank=True,
        null=True
    )
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ('SINGLE', 'Single'),
            ('MARRIED', 'Married'),
            ('DIVORCED', 'Divorced'),
            ('WIDOWED', 'Widowed'),
        ],
        blank=True,
        null=True
    )
    nationality = models.CharField(max_length=50, default='Zimbabwean')
    
    # Next of kin
    next_of_kin_name = models.CharField(max_length=200, blank=True, null=True)
    next_of_kin_relationship = models.CharField(max_length=50, blank=True, null=True)
    next_of_kin_phone = models.CharField(max_length=17, blank=True, null=True)
    next_of_kin_address = models.TextField(blank=True, null=True)
    
    # Social links
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    
    # Preferences
    timezone = models.CharField(max_length=50, default='Africa/Harare')
    language = models.CharField(
        max_length=10,
        default='en',
        choices=[
            ('en', 'English'),
            ('sn', 'Shona'),
            ('nd', 'Ndebele'),
        ]
    )
    
    # Privacy settings
    profile_visible_to_colleagues = models.BooleanField(default=True)
    phone_visible_to_colleagues = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')

    def __str__(self):
        return f'{self.user.email} Profile'

    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

    @property
    def full_address(self):
        """Return formatted full address"""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.suburb,
            self.city,
            self.province,
            self.postal_code,
            self.country
        ]
        return ', '.join(filter(None, address_parts))

    @property
    def is_profile_complete(self):
        """Check if profile has all required information"""
        required_fields = [
            self.phone_number,
            self.national_id,
            self.date_of_birth,
            self.gender,
            self.address_line_1,
            self.city,
        ]
        return all(required_fields)

    def get_completion_percentage(self):
        """Calculate profile completion percentage"""
        fields = [
            self.phone_number, self.alternate_phone, self.national_id,
            self.date_of_birth, self.gender, self.marital_status,
            self.address_line_1, self.city, self.province,
            self.next_of_kin_name, self.next_of_kin_phone,
            self.bio, self.avatar and self.avatar.name != 'avatars/default.png'
        ]
        completed = sum(1 for field in fields if field)
        return int((completed / len(fields)) * 100)


class LoginHistory(models.Model):
    """
    Track user login history for security auditing
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-login_time']
        verbose_name = 'Login History'
        verbose_name_plural = 'Login Histories'

    def __str__(self):
        return f"{self.user.email} - {self.login_time}"

    @property
    def session_duration(self):
        """Calculate session duration"""
        if self.logout_time:
            duration = self.logout_time - self.login_time
            return duration
        return None


class PasswordResetToken(models.Model):
    """
    Password reset token management
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Password reset for {self.user.email}"

    @property
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid"""
        return not self.is_used and not self.is_expired

    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


# Signals
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile automatically when a new user is created
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the profile when the user is saved
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()