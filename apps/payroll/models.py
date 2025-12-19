from django.db import models
from django.db.models import Sum, Q
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.employees.models import Employee
from decimal import Decimal
from datetime import date
from django.utils import timezone


class SalaryComponent(models.Model):
    """
    Salary components - earnings and deductions (Zimbabwe-specific)
    """
    class ComponentType(models.TextChoices):
        EARNING = 'EARNING', 'Earning'
        DEDUCTION = 'DEDUCTION', 'Deduction'
        ALLOWANCE = 'ALLOWANCE', 'Allowance'
        BONUS = 'BONUS', 'Bonus'
        REIMBURSEMENT = 'REIMBURSEMENT', 'Reimbursement'

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    type = models.CharField(max_length=15, choices=ComponentType.choices)
    description = models.TextField(blank=True, null=True)
    
    # Tax and statutory
    is_taxable = models.BooleanField(default=True)
    is_statutory = models.BooleanField(
        default=False,
        help_text="Statutory deductions (PAYE, NSSA, AIDS Levy)"
    )
    
    # Calculation settings
    is_fixed = models.BooleanField(
        default=True,
        help_text="Fixed amount vs percentage of basic salary"
    )
    is_percentage = models.BooleanField(default=False)
    percentage_of_basic = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of basic salary"
    )
    
    # Calculation based on attendance
    is_pro_rated = models.BooleanField(
        default=False,
        help_text="Pro-rate based on days worked"
    )
    
    # Display settings
    display_order = models.PositiveIntegerField(default=0)
    show_on_payslip = models.BooleanField(default=True)
    
    # Zimbabwe statutory components
    is_nssa = models.BooleanField(
        default=False,
        help_text="NSSA contribution"
    )
    is_paye = models.BooleanField(
        default=False,
        help_text="Pay As You Earn (Income Tax)"
    )
    is_aids_levy = models.BooleanField(
        default=False,
        help_text="AIDS Levy (3% of PAYE)"
    )
    
    # Pension/Retirement
    is_pension = models.BooleanField(default=False)
    is_medical_aid = models.BooleanField(default=False)
    
    # Special allowances
    is_housing_allowance = models.BooleanField(default=False)
    is_transport_allowance = models.BooleanField(default=False)
    is_meal_allowance = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['type', 'display_order', 'name']
        verbose_name = 'Salary Component'
        verbose_name_plural = 'Salary Components'

    def __str__(self):
        return f"{self.name} ({self.type})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join([word[0] for word in self.name.split()[:3]]).upper()
        super().save(*args, **kwargs)


class EmployeeSalary(models.Model):
    """
    Employee-specific salary components
    """
    employee = models.ForeignKey(
        Employee,
        related_name='salary_components',
        on_delete=models.CASCADE
    )
    component = models.ForeignKey(SalaryComponent, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Effective dates
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    # Override component settings
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'component', 'effective_from')
        ordering = ['employee', 'component']
        verbose_name = 'Employee Salary'
        verbose_name_plural = 'Employee Salaries'

    def __str__(self):
        return f"{self.employee}: {self.component.name} = ${self.amount}"

    @property
    def is_currently_effective(self):
        """Check if this salary component is currently effective"""
        today = date.today()
        if self.effective_to:
            return self.effective_from <= today <= self.effective_to
        return self.effective_from <= today


class TaxBracket(models.Model):
    """
    Zimbabwe PAYE tax brackets
    """
    year = models.PositiveIntegerField()
    min_income = models.DecimalField(max_digits=12, decimal_places=2)
    max_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Null means no upper limit"
    )
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Tax rate percentage"
    )
    fixed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Fixed tax amount for this bracket"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['year', 'min_income']
        unique_together = ('year', 'min_income')
        verbose_name = 'Tax Bracket'
        verbose_name_plural = 'Tax Brackets'

    def __str__(self):
        max_str = f"${self.max_income:,.2f}" if self.max_income else "and above"
        return f"{self.year}: ${self.min_income:,.2f} - {max_str} @ {self.rate}%"


class NSSAContribution(models.Model):
    """
    NSSA contribution rates for Zimbabwe
    """
    year = models.PositiveIntegerField(unique=True)
    employee_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.00'),
        help_text="Employee contribution percentage"
    )
    employer_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.00'),
        help_text="Employer contribution percentage"
    )
    minimum_wage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum pensionable wage"
    )
    maximum_wage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum pensionable wage"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year']
        verbose_name = 'NSSA Contribution'
        verbose_name_plural = 'NSSA Contributions'

    def __str__(self):
        return f"NSSA {self.year}: EE {self.employee_rate}% / ER {self.employer_rate}%"


class Payslip(models.Model):
    """
    Monthly payslips for employees
    """
    class PayslipStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        PROCESSED = 'PROCESSED', 'Processed'
        PAID = 'PAID', 'Paid'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(
        Employee,
        related_name='payslips',
        on_delete=models.PROTECT
    )
    payslip_number = models.CharField(max_length=50, unique=True, blank=True)
    
    # Pay period
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    payment_date = models.DateField()
    
    status = models.CharField(
        max_length=15,
        choices=PayslipStatus.choices,
        default=PayslipStatus.DRAFT
    )
    
    # Basic salary
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Attendance-based calculations
    total_working_days = models.PositiveIntegerField(default=0)
    days_worked = models.PositiveIntegerField(default=0)
    days_absent = models.PositiveIntegerField(default=0)
    leave_days = models.PositiveIntegerField(default=0)
    
    # Hours
    regular_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Totals
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Statutory deductions
    paye = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Pay As You Earn (Income Tax)"
    )
    nssa_employee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="NSSA Employee Contribution"
    )
    nssa_employer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="NSSA Employer Contribution"
    )
    aids_levy = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="AIDS Levy (3% of PAYE)"
    )
    
    # Other deductions
    pension = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    medical_aid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loans = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Net pay
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Additional information
    currency = models.CharField(
        max_length=3,
        default='USD',
        choices=[('USD', 'US Dollar'), ('ZWL', 'Zimbabwe Dollar')]
    )
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1,
        help_text="Exchange rate if paid in ZWL"
    )
    
    # Approval workflow
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prepared_payslips'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payslips'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Payment details
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('BANK_TRANSFER', 'Bank Transfer'),
            ('CASH', 'Cash'),
            ('CHEQUE', 'Cheque'),
            ('MOBILE_MONEY', 'Mobile Money'),
        ],
        default='BANK_TRANSFER'
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True, help_text="Internal notes (not shown to employee)")
    
    # Flags
    is_final = models.BooleanField(default=False)
    is_13th_cheque = models.BooleanField(default=False)
    is_bonus_payment = models.BooleanField(default=False)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pay_period_start', 'employee']
        unique_together = ('employee', 'pay_period_start', 'pay_period_end')
        indexes = [
            models.Index(fields=['employee', 'pay_period_start']),
            models.Index(fields=['status', 'payment_date']),
        ]
        verbose_name = 'Payslip'
        verbose_name_plural = 'Payslips'

    def __str__(self):
        return f"{self.payslip_number} - {self.employee} ({self.pay_period_start})"

    def save(self, *args, **kwargs):
        # Generate payslip number
        if not self.payslip_number:
            year_month = self.pay_period_start.strftime('%Y%m')
            last_payslip = Payslip.objects.filter(
                payslip_number__startswith=f'PS{year_month}'
            ).order_by('-payslip_number').first()
            
            if last_payslip:
                last_num = int(last_payslip.payslip_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.payslip_number = f'PS{year_month}{new_num:04d}'
        
        # Calculate totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Calculate all payslip totals"""
        # Calculate gross earnings
        earnings = self.entries.filter(
            component__type__in=['EARNING', 'ALLOWANCE', 'BONUS']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        self.gross_earnings = self.basic_salary + earnings
        
        # Calculate total allowances
        self.total_allowances = self.entries.filter(
            component__type='ALLOWANCE'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Calculate total deductions
        deductions = self.entries.filter(
            component__type='DEDUCTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        self.total_deductions = deductions + self.paye + self.nssa_employee + self.aids_levy
        
        # Calculate net pay
        self.net_pay = self.gross_earnings - self.total_deductions

    def calculate_paye(self):
        """Calculate PAYE (Pay As You Earn) tax for Zimbabwe"""
        annual_income = self.gross_earnings * 12
        
        # Get tax brackets for current year
        year = self.pay_period_start.year
        brackets = TaxBracket.objects.filter(year=year).order_by('min_income')
        
        total_tax = Decimal('0')
        remaining_income = annual_income
        
        for bracket in brackets:
            if remaining_income <= 0:
                break
            
            if bracket.max_income:
                taxable_in_bracket = min(
                    remaining_income,
                    bracket.max_income - bracket.min_income
                )
            else:
                taxable_in_bracket = remaining_income
            
            tax_in_bracket = (taxable_in_bracket * bracket.rate / 100) + bracket.fixed_amount
            total_tax += tax_in_bracket
            remaining_income -= taxable_in_bracket
        
        # Monthly PAYE
        monthly_paye = total_tax / 12
        return monthly_paye

    def calculate_nssa(self):
        """Calculate NSSA contributions"""
        year = self.pay_period_start.year
        try:
            nssa_config = NSSAContribution.objects.get(year=year, is_active=True)
        except NSSAContribution.DoesNotExist:
            return Decimal('0'), Decimal('0')
        
        # Cap salary at maximum pensionable wage
        pensionable_salary = min(self.basic_salary, nssa_config.maximum_wage)
        pensionable_salary = max(pensionable_salary, nssa_config.minimum_wage)
        
        employee_contribution = pensionable_salary * (nssa_config.employee_rate / 100)
        employer_contribution = pensionable_salary * (nssa_config.employer_rate / 100)
        
        return employee_contribution, employer_contribution

    def calculate_aids_levy(self):
        """Calculate AIDS Levy (3% of PAYE)"""
        return self.paye * Decimal('0.03')

    def process(self):
        """Process payslip - calculate all statutory deductions"""
        # Calculate PAYE
        self.paye = self.calculate_paye()
        
        # Calculate NSSA
        self.nssa_employee, self.nssa_employer = self.calculate_nssa()
        
        # Calculate AIDS Levy
        self.aids_levy = self.calculate_aids_levy()
        
        # Recalculate totals
        self.calculate_totals()
        
        # Update status
        if self.status == 'DRAFT':
            self.status = 'PENDING'
        
        self.save()

    def approve(self, user):
        """Approve payslip"""
        self.status = self.PayslipStatus.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def mark_as_paid(self, payment_ref=''):
        """Mark payslip as paid"""
        self.status = self.PayslipStatus.PAID
        self.payment_reference = payment_ref
        self.save()


class PayslipEntry(models.Model):
    """
    Individual line items on a payslip
    """
    payslip = models.ForeignKey(
        Payslip,
        related_name='entries',
        on_delete=models.CASCADE
    )
    component = models.ForeignKey(SalaryComponent, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Calculation details
    calculation_basis = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        help_text="For components like overtime hours"
    )
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Rate per unit for calculated components"
    )
    
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['component__type', 'component__display_order']
        verbose_name = 'Payslip Entry'
        verbose_name_plural = 'Payslip Entries'

    def __str__(self):
        return f"{self.component.name}: ${self.amount}"

    def save(self, *args, **kwargs):
        # Calculate amount if rate and quantity provided
        if self.rate and self.quantity:
            self.amount = self.rate * self.quantity
        
        super().save(*args, **kwargs)


class PayrollBatch(models.Model):
    """
    Batch processing of multiple payslips
    """
    class BatchStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    batch_number = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    payment_date = models.DateField()
    
    status = models.CharField(
        max_length=15,
        choices=BatchStatus.choices,
        default=BatchStatus.DRAFT
    )
    
    # Filters for employees to include
    departments = models.ManyToManyField(
        'employees.Department',
        blank=True
    )
    employment_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of employment types to include"
    )
    
    # Statistics
    total_employees = models.PositiveIntegerField(default=0)
    processed_employees = models.PositiveIntegerField(default=0)
    failed_employees = models.PositiveIntegerField(default=0)
    
    total_gross = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_payroll_batches'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payroll_batches'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payroll Batch'
        verbose_name_plural = 'Payroll Batches'

    def __str__(self):
        return f"{self.batch_number} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.batch_number:
            year_month = self.pay_period_start.strftime('%Y%m')
            last_batch = PayrollBatch.objects.filter(
                batch_number__startswith=f'PB{year_month}'
            ).order_by('-batch_number').first()
            
            if last_batch:
                last_num = int(last_batch.batch_number[-3:])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.batch_number = f'PB{year_month}{new_num:03d}'
        
        super().save(*args, **kwargs)
