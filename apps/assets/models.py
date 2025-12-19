from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.employees.models import Employee
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone


class AssetCategory(models.Model):
    """
    Asset categories for organization
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    
    # Depreciation settings
    default_depreciation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Annual depreciation rate percentage"
    )
    default_useful_life_years = models.PositiveIntegerField(
        default=5,
        help_text="Expected useful life in years"
    )
    
    # Maintenance settings
    requires_regular_maintenance = models.BooleanField(default=False)
    maintenance_interval_days = models.PositiveIntegerField(
        default=90,
        help_text="Days between maintenance checks"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Asset Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name[:5].upper()
        super().save(*args, **kwargs)

    @property
    def total_assets(self):
        """Count total assets in this category"""
        return self.assets.count()

    @property
    def total_value(self):
        """Calculate total current value of all assets"""
        return sum(asset.current_value for asset in self.assets.all())


class Asset(models.Model):
    """
    Organization assets with comprehensive tracking
    """
    class AssetStatus(models.TextChoices):
        IN_STOCK = 'IN_STOCK', 'In Stock'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_REPAIR = 'IN_REPAIR', 'In Repair'
        IN_MAINTENANCE = 'IN_MAINTENANCE', 'In Maintenance'
        DISPOSED = 'DISPOSED', 'Disposed'
        LOST = 'LOST', 'Lost'
        STOLEN = 'STOLEN', 'Stolen'
        DAMAGED = 'DAMAGED', 'Damaged Beyond Repair'
        RETIRED = 'RETIRED', 'Retired'

    class AssetCondition(models.TextChoices):
        EXCELLENT = 'EXCELLENT', 'Excellent'
        GOOD = 'GOOD', 'Good'
        FAIR = 'FAIR', 'Fair'
        POOR = 'POOR', 'Poor'
        DAMAGED = 'DAMAGED', 'Damaged'

    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        AssetCategory,
        related_name='assets',
        on_delete=models.PROTECT
    )
    description = models.TextField(blank=True, null=True)
    
    # Identification
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    asset_tag = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    qr_code = models.ImageField(upload_to='asset_qr_codes/', blank=True, null=True)
    
    # Financial information
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    current_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current estimated value after depreciation"
    )
    salvage_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Estimated value at end of useful life"
    )
    
    # Vendor information
    vendor_name = models.CharField(max_length=200, blank=True)
    vendor_contact = models.CharField(max_length=100, blank=True)
    purchase_order_number = models.CharField(max_length=100, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    
    # Warranty
    warranty_expiry_date = models.DateField(null=True, blank=True)
    warranty_terms = models.TextField(blank=True)
    warranty_provider = models.CharField(max_length=200, blank=True)
    
    # Technical specifications
    manufacturer = models.CharField(max_length=200, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    
    # Status and condition
    status = models.CharField(
        max_length=20,
        choices=AssetStatus.choices,
        default=AssetStatus.IN_STOCK
    )
    condition = models.CharField(
        max_length=20,
        choices=AssetCondition.choices,
        default=AssetCondition.GOOD
    )
    
    # Assignment
    current_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets'
    )
    current_location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Physical location of asset"
    )
    department = models.ForeignKey(
        'employees.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='department_assets'
    )
    
    # Maintenance
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    maintenance_notes = models.TextField(blank=True)
    
    # Insurance
    is_insured = models.BooleanField(default=False)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    insurance_expiry_date = models.DateField(null=True, blank=True)
    insurance_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Disposal information
    disposal_date = models.DateField(null=True, blank=True)
    disposal_method = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('SOLD', 'Sold'),
            ('DONATED', 'Donated'),
            ('SCRAPPED', 'Scrapped'),
            ('TRADED', 'Traded In'),
            ('RECYCLED', 'Recycled'),
        ]
    )
    disposal_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    disposal_notes = models.TextField(blank=True)
    
    # Attachments
    photo = models.ImageField(upload_to='asset_photos/', blank=True, null=True)
    
    # Flags
    is_critical = models.BooleanField(
        default=False,
        help_text="Critical asset requiring special attention"
    )
    is_portable = models.BooleanField(default=False)
    requires_checkout = models.BooleanField(
        default=True,
        help_text="Requires formal checkout process"
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assets'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_tag', 'status']),
            models.Index(fields=['serial_number']),
        ]

    def __str__(self):
        return f"{self.name} ({self.asset_tag})"

    def save(self, *args, **kwargs):
        # Auto-generate asset tag
        if not self.asset_tag:
            category_code = self.category.code[:3]
            year = date.today().year
            last_asset = Asset.objects.filter(
                asset_tag__startswith=f'{category_code}-{year}'
            ).order_by('-asset_tag').first()
            
            if last_asset:
                last_num = int(last_asset.asset_tag.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.asset_tag = f'{category_code}-{year}-{new_num:05d}'
        
        # Calculate current value (depreciation)
        if self.purchase_cost and self.purchase_date and not self.current_value:
            self.current_value = self.calculate_depreciated_value()
        
        # Set next maintenance date
        if self.category.requires_regular_maintenance and not self.next_maintenance_date:
            if self.last_maintenance_date:
                self.next_maintenance_date = self.last_maintenance_date + timedelta(
                    days=self.category.maintenance_interval_days
                )
            else:
                self.next_maintenance_date = date.today() + timedelta(
                    days=self.category.maintenance_interval_days
                )
        
        super().save(*args, **kwargs)

    def calculate_depreciated_value(self):
        """Calculate current value based on straight-line depreciation"""
        if not self.purchase_cost or not self.purchase_date:
            return self.purchase_cost or Decimal('0')
        
        years_owned = (date.today() - self.purchase_date).days / 365.25
        depreciation_rate = self.category.default_depreciation_rate / 100
        
        annual_depreciation = (self.purchase_cost - self.salvage_value) * depreciation_rate
        total_depreciation = min(
            annual_depreciation * Decimal(str(years_owned)),
            self.purchase_cost - self.salvage_value
        )
        
        return max(self.purchase_cost - total_depreciation, self.salvage_value)

    @property
    def age_in_years(self):
        """Calculate asset age in years"""
        if self.purchase_date:
            return (date.today() - self.purchase_date).days / 365.25
        return 0

    @property
    def is_under_warranty(self):
        """Check if asset is still under warranty"""
        if self.warranty_expiry_date:
            return date.today() <= self.warranty_expiry_date
        return False

    @property
    def is_maintenance_due(self):
        """Check if maintenance is due"""
        if self.next_maintenance_date:
            return date.today() >= self.next_maintenance_date
        return False

    @property
    def days_until_maintenance(self):
        """Days until next maintenance"""
        if self.next_maintenance_date:
            return (self.next_maintenance_date - date.today()).days
        return None

    @property
    def is_insurance_expiring_soon(self):
        """Check if insurance expires within 30 days"""
        if self.insurance_expiry_date:
            days_until = (self.insurance_expiry_date - date.today()).days
            return 0 < days_until <= 30
        return False


class AssetAssignment(models.Model):
    """
    Track asset assignments to employees
    """
    class AssignmentStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        RETURNED = 'RETURNED', 'Returned'
        DAMAGED = 'DAMAGED', 'Returned Damaged'
        LOST = 'LOST', 'Lost'
        STOLEN = 'STOLEN', 'Stolen'

    asset = models.ForeignKey(
        Asset,
        related_name='assignments',
        on_delete=models.CASCADE
    )
    employee = models.ForeignKey(
        Employee,
        related_name='asset_history',
        on_delete=models.CASCADE
    )
    
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_assets'
    )
    assigned_date = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_date = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE
    )
    
    # Condition tracking
    condition_out = models.TextField(
        blank=True,
        help_text="Condition of asset upon assignment"
    )
    condition_in = models.TextField(
        blank=True,
        null=True,
        help_text="Condition of asset upon return"
    )
    
    # Responsibility
    responsibility_agreement = models.BooleanField(
        default=False,
        help_text="Employee accepted responsibility"
    )
    agreement_signed_at = models.DateTimeField(null=True, blank=True)
    
    # Charges/damages
    damage_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Charge for damages"
    )
    damage_description = models.TextField(blank=True)
    
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assigned_date']
        indexes = [
            models.Index(fields=['asset', 'status']),
            models.Index(fields=['employee', 'assigned_date']),
        ]

    def __str__(self):
        return f"{self.asset} -> {self.employee} on {self.assigned_date.date()}"

    @property
    def duration_days(self):
        """Calculate assignment duration"""
        end_date = self.returned_date or timezone.now()
        return (end_date - self.assigned_date).days

    @property
    def is_overdue(self):
        """Check if return is overdue"""
        if self.expected_return_date and self.status == 'ACTIVE':
            return date.today() > self.expected_return_date
        return False


class AssetMaintenance(models.Model):
    """
    Track asset maintenance records
    """
    class MaintenanceType(models.TextChoices):
        ROUTINE = 'ROUTINE', 'Routine Maintenance'
        REPAIR = 'REPAIR', 'Repair'
        UPGRADE = 'UPGRADE', 'Upgrade'
        INSPECTION = 'INSPECTION', 'Inspection'
        CLEANING = 'CLEANING', 'Cleaning'
        CALIBRATION = 'CALIBRATION', 'Calibration'

    class MaintenanceStatus(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    asset = models.ForeignKey(
        Asset,
        related_name='maintenance_records',
        on_delete=models.CASCADE
    )
    maintenance_type = models.CharField(
        max_length=20,
        choices=MaintenanceType.choices
    )
    status = models.CharField(
        max_length=20,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.SCHEDULED
    )
    
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    
    description = models.TextField()
    work_performed = models.TextField(blank=True)
    
    # Service provider
    performed_by = models.CharField(max_length=200, blank=True)
    service_provider = models.CharField(max_length=200, blank=True)
    
    # Cost
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    invoice_number = models.CharField(max_length=100, blank=True)
    
    # Parts used
    parts_replaced = models.TextField(blank=True)
    
    # Follow-up
    requires_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.asset} - {self.maintenance_type} on {self.scheduled_date}"


class AssetDepreciation(models.Model):
    """
    Track asset depreciation over time
    """
    asset = models.ForeignKey(
        Asset,
        related_name='depreciation_records',
        on_delete=models.CASCADE
    )
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    
    opening_value = models.DecimalField(max_digits=12, decimal_places=2)
    depreciation_amount = models.DecimalField(max_digits=12, decimal_places=2)
    closing_value = models.DecimalField(max_digits=12, decimal_places=2)
    
    depreciation_method = models.CharField(
        max_length=20,
        choices=[
            ('STRAIGHT_LINE', 'Straight Line'),
            ('DECLINING_BALANCE', 'Declining Balance'),
            ('UNITS_OF_PRODUCTION', 'Units of Production'),
        ],
        default='STRAIGHT_LINE'
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('asset', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.asset} - {self.month}/{self.year}"