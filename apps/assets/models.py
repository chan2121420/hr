from django.db import models
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee

class AssetCategory(TimeStampedModel):
    """Asset categories"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Asset Categories'
    
    def __str__(self):
        return self.name

class Asset(TimeStampedModel):
    """Company assets"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Under Maintenance'),
        ('damaged', 'Damaged'),
        ('retired', 'Retired'),
    ]
    
    CONDITION_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ]
    
    # Basic info
    asset_tag = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    
    # Details
    manufacturer = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    
    # Financial
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    
    # Location
    location = models.CharField(max_length=200, blank=True)
    
    # Image
    image = models.ImageField(upload_to='asset_images/', null=True, blank=True)
    
    class Meta:
        ordering = ['asset_tag']
    
    def __str__(self):
        return f"{self.asset_tag} - {self.name}"

class AssetAssignment(TimeStampedModel):
    """Asset assignments to employees"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('returned', 'Returned'),
    ]
    
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='assignments')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='asset_assignments')
    
    assigned_date = models.DateField()
    expected_return_date = models.DateField(null=True, blank=True)
    actual_return_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    assigned_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    return_condition = models.CharField(max_length=20, blank=True)
    return_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.asset.name} -> {self.employee.get_full_name()}"