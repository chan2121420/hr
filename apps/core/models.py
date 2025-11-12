from django.db import models
from django.contrib.auth import get_user_model

class TimeStampedModel(models.Model):
    """Abstract base model with timestamp fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class Company(models.Model):
    """Multi-company support"""
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    tax_number = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Zimbabwe')
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Companies'
    
    def __str__(self):
        return self.name

class Department(TimeStampedModel):
    """Organization departments"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_departments')
    manager = models.ForeignKey('employees.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['company', 'code']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"