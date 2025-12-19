"""
Enhanced Payroll Calculation Utilities
Includes Zimbabwe ZIMRA tax calculations and NSSA contributions
Updated for 2024/2025 tax year
"""

from decimal import Decimal
from apps.employees.models import Employee
from .models import EmployeeSalary, Payslip, PayslipEntry, SalaryComponent
import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================
# ZIMBABWE TAX & CONTRIBUTION RATES (USD)
# ============================================

# NSSA (National Social Security Authority) Rates
NSSA_EMPLOYEE_RATE = Decimal('0.035')  # 3.5%
NSSA_EMPLOYER_RATE = Decimal('0.035')  # 3.5%
NSSA_CEILING_USD = Decimal('1000.00')  # Maximum insurable earnings

# USD PAYE Tax Bands (2024/2025)
PAYE_BANDS_USD = [
    {'min': Decimal('0'), 'max': Decimal('500'), 'rate': Decimal('0.00'), 'deduction': Decimal('0')},
    {'min': Decimal('500.01'), 'max': Decimal('2500'), 'rate': Decimal('0.20'), 'deduction': Decimal('100')},
    {'min': Decimal('2500.01'), 'max': Decimal('5000'), 'rate': Decimal('0.25'), 'deduction': Decimal('225')},
    {'min': Decimal('5000.01'), 'max': Decimal('10000'), 'rate': Decimal('0.30'), 'deduction': Decimal('475')},
    {'min': Decimal('10000.01'), 'max': None, 'rate': Decimal('0.35'), 'deduction': Decimal('975')},
]

# AIDS Levy
AIDS_LEVY_RATE = Decimal('0.03')  # 3% of PAYE

# Tax Credits (Monthly)
STANDARD_TAX_CREDIT = Decimal('0')  # Currently no standard credit in Zimbabwe


def calculate_nssa_employee(gross_earnings):
    """
    Calculate NSSA employee contribution
    
    Args:
        gross_earnings: Gross monthly earnings
        
    Returns:
        Decimal: NSSA contribution amount
    """
    insurable_earnings = min(gross_earnings, NSSA_CEILING_USD)
    nssa = (insurable_earnings * NSSA_EMPLOYEE_RATE).quantize(Decimal('0.01'))
    return nssa


def calculate_nssa_employer(gross_earnings):
    """
    Calculate NSSA employer contribution (for reference)
    
    Args:
        gross_earnings: Gross monthly earnings
        
    Returns:
        Decimal: Employer NSSA contribution amount
    """
    insurable_earnings = min(gross_earnings, NSSA_CEILING_USD)
    nssa = (insurable_earnings * NSSA_EMPLOYER_RATE).quantize(Decimal('0.01'))
    return nssa


def calculate_paye(taxable_income):
    """
    Calculate PAYE (Pay As You Earn) tax using Zimbabwe tax bands
    
    Args:
        taxable_income: Income after NSSA and other allowable deductions
        
    Returns:
        Decimal: PAYE amount
    """
    if taxable_income <= Decimal('0'):
        return Decimal('0.00')
    
    paye = Decimal('0.00')
    
    for band in PAYE_BANDS_USD:
        min_band = band['min']
        max_band = band['max']
        rate = band['rate']
        deduction = band['deduction']
        
        if max_band is None:
            # Top band - unlimited
            paye = (taxable_income * rate) - deduction
            break
        elif taxable_income <= max_band:
            # Income falls within this band
            paye = (taxable_income * rate) - deduction
            break
    
    # Apply tax credit if any
    paye = max(Decimal('0.00'), paye - STANDARD_TAX_CREDIT)
    
    return paye.quantize(Decimal('0.01'))


def calculate_aids_levy(paye_amount):
    """
    Calculate AIDS Levy (3% of PAYE)
    
    Args:
        paye_amount: PAYE tax amount
        
    Returns:
        Decimal: AIDS Levy amount
    """
    if paye_amount <= Decimal('0'):
        return Decimal('0.00')
    
    levy = (paye_amount * AIDS_LEVY_RATE).quantize(Decimal('0.01'))
    return levy


def get_or_create_statutory_components():
    """
    Ensure all statutory components exist in the database
    
    Returns:
        dict: Dictionary of component objects
    """
    components = {}
    
    statutory_components = [
        {
            'name': 'NSSA Employee',
            'type': 'DEDUCTION',
            'is_statutory': True,
            'is_taxable': False,
            'description': 'National Social Security Authority - Employee Contribution'
        },
        {
            'name': 'PAYE',
            'type': 'DEDUCTION',
            'is_statutory': True,
            'is_taxable': False,
            'description': 'Pay As You Earn - Income Tax'
        },
        {
            'name': 'AIDS Levy',
            'type': 'DEDUCTION',
            'is_statutory': True,
            'is_taxable': False,
            'description': 'AIDS Levy (3% of PAYE)'
        },
    ]
    
    for comp_data in statutory_components:
        component, created = SalaryComponent.objects.get_or_create(
            name=comp_data['name'],
            defaults={
                'type': comp_data['type'],
                'is_statutory': comp_data['is_statutory'],
                'is_taxable': comp_data['is_taxable']
            }
        )
        components[comp_data['name']] = component
        
        if created:
            logger.info(f"Created statutory component: {comp_data['name']}")
    
    return components


def calculate_taxable_income(gross_earnings, pre_tax_deductions):
    """
    Calculate taxable income after allowable deductions
    
    Args:
        gross_earnings: Total gross earnings
        pre_tax_deductions: Sum of pre-tax deductions (e.g., NSSA)
        
    Returns:
        Decimal: Taxable income
    """
    taxable = gross_earnings - pre_tax_deductions
    return max(Decimal('0.00'), taxable)


def generate_payslip_for_employee(employee, start_date, end_date):
    """
    Generate a complete payslip for an employee with Zimbabwe tax calculations
    
    Args:
        employee: Employee object
        start_date: Pay period start date
        end_date: Pay period end date
        
    Returns:
        Payslip: Generated payslip object
        
    Raises:
        Exception: If payslip already exists or calculation errors occur
    """
    # Check if payslip already exists
    if Payslip.objects.filter(employee=employee, pay_period_start=start_date).exists():
        raise Exception(f"Payslip already exists for {employee} for period starting {start_date}")
    
    logger.info(f"Generating payslip for {employee} ({start_date} to {end_date})")
    
    # Get employee salary components
    salary_components = employee.salary_components.all().select_related('component')
    
    if not salary_components.exists():
        raise Exception(f"No salary components found for {employee}")
    
    # Initialize calculation variables
    gross_earnings = Decimal('0.00')
    taxable_earnings = Decimal('0.00')
    non_taxable_earnings = Decimal('0.00')
    pre_tax_deductions = Decimal('0.00')
    post_tax_deductions = Decimal('0.00')
    
    # Create payslip
    payslip = Payslip.objects.create(
        employee=employee,
        pay_period_start=start_date,
        pay_period_end=end_date,
        status='PENDING'
    )
    
    entries = []
    
    # ==========================================
    # STEP 1: Calculate Earnings
    # ==========================================
    earning_components = salary_components.filter(component__type='EARNING')
    
    for item in earning_components:
        amount = item.amount
        gross_earnings += amount
        
        if item.component.is_taxable:
            taxable_earnings += amount
        else:
            non_taxable_earnings += amount
        
        entries.append(PayslipEntry(
            payslip=payslip,
            component=item.component,
            amount=amount
        ))
        
        logger.debug(f"Added earning: {item.component.name} = ${amount}")
    
    # ==========================================
    # STEP 2: Calculate NSSA (Pre-tax)
    # ==========================================
    statutory_components = get_or_create_statutory_components()
    
    nssa_deduction = calculate_nssa_employee(gross_earnings)
    pre_tax_deductions += nssa_deduction
    
    entries.append(PayslipEntry(
        payslip=payslip,
        component=statutory_components['NSSA Employee'],
        amount=-nssa_deduction  # Negative for deductions
    ))
    
    logger.debug(f"NSSA Employee: ${nssa_deduction}")
    
    # ==========================================
    # STEP 3: Calculate Taxable Income
    # ==========================================
    taxable_income = calculate_taxable_income(taxable_earnings, pre_tax_deductions)
    logger.debug(f"Taxable Income: ${taxable_income}")
    
    # ==========================================
    # STEP 4: Calculate PAYE
    # ==========================================
    paye_amount = calculate_paye(taxable_income)
    
    entries.append(PayslipEntry(
        payslip=payslip,
        component=statutory_components['PAYE'],
        amount=-paye_amount
    ))
    
    logger.debug(f"PAYE: ${paye_amount}")
    
    # ==========================================
    # STEP 5: Calculate AIDS Levy
    # ==========================================
    aids_levy_amount = calculate_aids_levy(paye_amount)
    
    entries.append(PayslipEntry(
        payslip=payslip,
        component=statutory_components['AIDS Levy'],
        amount=-aids_levy_amount
    ))
    
    logger.debug(f"AIDS Levy: ${aids_levy_amount}")
    
    # ==========================================
    # STEP 6: Calculate Other Post-Tax Deductions
    # ==========================================
    deduction_components = salary_components.filter(
        component__type='DEDUCTION',
        component__is_statutory=False
    )
    
    for item in deduction_components:
        amount = item.amount
        post_tax_deductions += amount
        
        entries.append(PayslipEntry(
            payslip=payslip,
            component=item.component,
            amount=-amount
        ))
        
        logger.debug(f"Added deduction: {item.component.name} = ${amount}")
    
    # ==========================================
    # STEP 7: Calculate Final Amounts
    # ==========================================
    total_statutory_deductions = nssa_deduction + paye_amount + aids_levy_amount
    total_deductions = pre_tax_deductions + paye_amount + aids_levy_amount + post_tax_deductions
    net_pay = gross_earnings - total_deductions
    
    # Ensure net pay is not negative
    if net_pay < Decimal('0.00'):
        logger.warning(f"Negative net pay for {employee}: ${net_pay}")
        net_pay = Decimal('0.00')
    
    # ==========================================
    # STEP 8: Save Payslip Entries
    # ==========================================
    PayslipEntry.objects.bulk_create(entries)
    
    # ==========================================
    # STEP 9: Update and Save Payslip
    # ==========================================
    payslip.gross_earnings = gross_earnings
    payslip.total_deductions = total_deductions
    payslip.net_pay = net_pay
    payslip.status = 'GENERATED'
    payslip.save()
    
    logger.info(f"Payslip generated successfully for {employee}")
    logger.info(f"Gross: ${gross_earnings}, Deductions: ${total_deductions}, Net: ${net_pay}")
    
    return payslip


def generate_bulk_payslips(month, year, employee_ids=None):
    """
    Generate payslips for multiple employees
    
    Args:
        month: Pay period month (1-12)
        year: Pay period year
        employee_ids: List of employee IDs (None = all active employees)
        
    Returns:
        dict: Summary of generation results
    """
    import calendar
    
    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)
    
    # Get employees
    if employee_ids:
        employees = Employee.objects.filter(
            id__in=employee_ids,
            status='ACTIVE'
        )
    else:
        employees = Employee.objects.filter(status='ACTIVE')
    
    results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'total': employees.count()
    }
    
    for employee in employees:
        try:
            # Check if already exists
            if Payslip.objects.filter(
                employee=employee,
                pay_period_start=start_date
            ).exists():
                results['skipped'].append({
                    'employee': str(employee),
                    'reason': 'Payslip already exists'
                })
                continue
            
            # Generate payslip
            payslip = generate_payslip_for_employee(employee, start_date, end_date)
            results['success'].append({
                'employee': str(employee),
                'payslip_id': payslip.id,
                'net_pay': float(payslip.net_pay)
            })
            
        except Exception as e:
            logger.error(f"Failed to generate payslip for {employee}: {str(e)}")
            results['failed'].append({
                'employee': str(employee),
                'error': str(e)
            })
    
    return results


def recalculate_payslip(payslip):
    """
    Recalculate an existing payslip (useful if salary components changed)
    
    Args:
        payslip: Payslip object to recalculate
        
    Returns:
        Payslip: Updated payslip
    """
    # Delete old entries
    payslip.entries.all().delete()
    
    # Delete the payslip
    payslip.delete()
    
    # Generate new payslip
    return generate_payslip_for_employee(
        payslip.employee,
        payslip.pay_period_start,
        payslip.pay_period_end
    )