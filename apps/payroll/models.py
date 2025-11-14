from django.db import models
from django.db.models import Sum
from apps.employees.models import Employee
from decimal import Decimal

class SalaryComponent(models.Model):
    class ComponentType(models.TextChoices):
        EARNING = 'EARNING', 'Earning'
        DEDUCTION = 'DEDUCTION', 'Deduction'

    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=ComponentType.choices)
    is_taxable = models.BooleanField(default=True)
    is_statutory = models.BooleanField(default=False) # e.g., NSSA, PAYE

    def __str__(self):
        return f"{self.name} ({self.type})"

class EmployeeSalary(models.Model):
    employee = models.ForeignKey(Employee, related_name='salary_components', on_delete=models.CASCADE)
    component = models.ForeignKey(SalaryComponent, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('employee', 'component')

    def __str__(self):
        return f"{self.employee}: {self.component.name} = {self.amount}"

class Payslip(models.Model):
    class PayslipStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        GENERATED = 'GENERATED', 'Generated'
        PAID = 'PAID', 'Paid'

    employee = models.ForeignKey(Employee, related_name='payslips', on_delete=models.PROTECT)
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    status = models.CharField(max_length=10, choices=PayslipStatus.choices, default=PayslipStatus.PENDING)
    
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payslip for {self.employee} ({self.pay_period_start} to {self.pay_period_end})"

    class Meta:
        ordering = ['-pay_period_start']

class PayslipEntry(models.Model):
    payslip = models.ForeignKey(Payslip, related_name='entries', on_delete=models.CASCADE)
    component = models.ForeignKey(SalaryComponent, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.component.name}: {self.amount}"