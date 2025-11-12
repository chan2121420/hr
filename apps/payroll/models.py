from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee
from decimal import Decimal

class PayrollComponent(TimeStampedModel):
    """Salary components (allowances/deductions)"""
    COMPONENT_TYPES = [
        ('earning', 'Earning'),
        ('deduction', 'Deduction'),
    ]
    
    CALCULATION_TYPES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Basic'),
        ('formula', 'Custom Formula'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    component_type = models.CharField(max_length=10, choices=COMPONENT_TYPES)
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPES)
    
    # For percentage-based
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # For fixed
    default_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # For formula
    formula = models.TextField(blank=True)  # e.g., "basic * 0.15 + allowances"
    
    is_taxable = models.BooleanField(default=True)
    is_statutory = models.BooleanField(default=False)  # PAYE, NSSA, etc.
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['component_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"

class EmployeePayrollComponent(TimeStampedModel):
    """Employee-specific salary components"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_components')
    component = models.ForeignKey(PayrollComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['employee', 'component', 'effective_from']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.component.name}"

class PayrollPeriod(TimeStampedModel):
    """Payroll periods"""
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    payment_date = models.DateField()
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    is_finalized = models.BooleanField(default=False)
    processed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Totals
    total_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_date']
        unique_together = ['start_date', 'end_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
class Payslip(TimeStampedModel):
    """Individual employee payslips"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name='payslips')
    
    # Basic salary
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Working days
    total_working_days = models.IntegerField()
    days_worked = models.DecimalField(max_digits=5, decimal_places=1)
    days_absent = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    
    # Earnings
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Deductions
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Tax and statutory
    paye_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nssa_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nssa_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Net salary
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    
    currency = models.CharField(max_length=3, default='USD')
    
    # Payment
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='Bank Transfer')
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # PDF generation
    pdf_file = models.FileField(upload_to='payslips/%Y/%m/', null=True, blank=True)
    
    class Meta:
        unique_together = ['employee', 'period']
        # ✅ Remove related field lookups
        ordering = ['-period_id']  # order by the ForeignKey itself
        indexes = [
            models.Index(fields=['employee', 'period']),  # index the direct fields only
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.period.name}"

class PayslipComponent(TimeStampedModel):
    """Individual components in a payslip"""
    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name='components')
    component = models.ForeignKey(PayrollComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['payslip', 'component']
    
    def __str__(self):
        return f"{self.component.name}: {self.amount}"

class LoanAdvance(TimeStampedModel):
    """Employee loans and salary advances"""
    LOAN_STATUS = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('repaying', 'Under Repayment'),
        ('completed', 'Fully Repaid'),
        ('defaulted', 'Defaulted'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='loans')
    loan_type = models.CharField(max_length=20, choices=[('loan', 'Loan'), ('advance', 'Salary Advance')])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()
    
    # Terms
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Annual %
    installment_count = models.IntegerField()
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    
    # Status
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='pending')
    amount_repaid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Approval
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def balance(self):
        return self.amount - self.amount_repaid
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.loan_type.title()} ({self.amount})"
