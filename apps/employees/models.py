from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Designation(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

class Employee(models.Model):
    class EmploymentStatus(models.TextChoices):
        PROBATION = 'PROBATION', 'Probation'
        ACTIVE = 'ACTIVE', 'Active'
        ON_LEAVE = 'ON_LEAVE', 'On Leave'
        TERMINATED = 'TERMINATED', 'Terminated'

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full-Time'
        PART_TIME = 'PART_TIME', 'Part-Time'
        CONTRACT = 'CONTRACT', 'Contract'
        INTERN = 'INTERN', 'Intern'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='employee_profile'
    )
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True)
    manager = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subordinates'
    )
    
    join_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20, 
        choices=EmploymentStatus.choices, 
        default=EmploymentStatus.PROBATION
    )
    employment_type = models.CharField(
        max_length=20, 
        choices=EmploymentType.choices, 
        default=EmploymentType.FULL_TIME
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.employee_id})"

    def save(self, *args, **kwargs):
        if not self.employee_id:
            last_employee = Employee.objects.all().order_by('id').last()
            next_id = (last_employee.id + 1) if last_employee else 1
            self.employee_id = f'EMP-{next_id:05d}'
        super().save(*args, **kwargs)

class EmergencyContact(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class BankDetails(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='bank_details')
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    branch_name = models.CharField(max_length=100, blank=True)
    branch_code = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"{self.employee}'s Bank Details"

class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50)
    document = models.FileField(upload_to='employee_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.document_type} for {self.employee}"

@receiver(post_save, sender=Employee)
def create_employee_bank_details(sender, instance, created, **kwargs):
    if created:
        BankDetails.objects.create(employee=instance)