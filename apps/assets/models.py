from django.db import models
from django.conf import settings
from apps.employees.models import Employee

class AssetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Asset Categories"

class Asset(models.Model):
    class AssetStatus(models.TextChoices):
        IN_STOCK = 'IN_STOCK', 'In Stock'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_REPAIR = 'IN_REPAIR', 'In Repair'
        DISPOSED = 'DISPOSED', 'Disposed'

    name = models.CharField(max_length=200)
    category = models.ForeignKey(AssetCategory, related_name='assets', on_delete=models.PROTECT)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    asset_tag = models.CharField(max_length=100, unique=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    warranty_expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=AssetStatus.choices, default=AssetStatus.IN_STOCK)
    current_employee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_assets'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.asset_tag})"

    def save(self, *args, **kwargs):
        if not self.asset_tag:
            last_asset = Asset.objects.all().order_by('id').last()
            next_id = (last_asset.id + 1) if last_asset else 1
            self.asset_tag = f'AST-{next_id:05d}'
        super().save(*args, **kwargs)

class AssetAssignment(models.Model):
    asset = models.ForeignKey(Asset, related_name='assignments', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, related_name='asset_history', on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    assigned_date = models.DateTimeField(auto_now_add=True)
    returned_date = models.DateTimeField(null=True, blank=True)
    condition_out = models.TextField(blank=True, help_text="Condition of asset upon assignment")
    condition_in = models.TextField(blank=True, null=True, help_text="Condition of asset upon return")

    def __str__(self):
        return f"{self.asset} -> {self.employee} on {self.assigned_date.date()}"

    class Meta:
        ordering = ['-assigned_date']