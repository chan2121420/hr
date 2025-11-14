from decimal import Decimal
from apps.employees.models import Employee
from .models import EmployeeSalary, Payslip, PayslipEntry, SalaryComponent
import datetime

# --- ZIMRA & NSSA Tax Configuration (USD - Example) ---
# These values should be moved to a settings or database model for easy updates
NSSA_RATE = Decimal('0.035')
NSSA_CEILING_USD = Decimal('700.00')

# USD PAYE Tax Bands (Example as of late 2024/2025)
PAYE_BANDS_USD = [
    {'min': 0, 'max': 300, 'rate': Decimal('0.00')},
    {'min': 300.01, 'max': 1500, 'rate': Decimal('0.20')},
    {'min': 1500.01, 'max': 3000, 'rate': Decimal('0.30')},
    {'min': 3000.01, 'max': 5000, 'rate': Decimal('0.35')},
    {'min': 5000.01, 'max': None, 'rate': Decimal('0.40')},
]
AIDS_LEVY_RATE = Decimal('0.03')
# ---------------------------------------------------

def calculate_nssa(gross_earnings):
    insurable_earnings = min(gross_earnings, NSSA_CEILING_USD)
    return (insurable_earnings * NSSA_RATE).quantize(Decimal('0.01'))

def calculate_paye(taxable_income):
    paye = Decimal('0.00')
    
    for band in PAYE_BANDS_USD:
        min_band = Decimal(band['min'])
        
        if band['max'] is None:
            taxable_in_band = taxable_income - (min_band - Decimal('0.01'))
            paye += taxable_in_band * band['rate']
            break
            
        max_band = Decimal(band['max'])
        
        if taxable_income > max_band:
            taxable_in_band = max_band - (min_band - Decimal('0.01'))
            paye += taxable_in_band * band['rate']
        elif taxable_income >= min_band:
            taxable_in_band = taxable_income - (min_band - Decimal('0.01'))
            paye += taxable_in_band * band['rate']
            break
            
    return paye.quantize(Decimal('0.01'))

def generate_payslip_for_employee(employee, start_date, end_date):
    if Payslip.objects.filter(employee=employee, pay_period_start=start_date).exists():
        raise Exception(f"Payslip already exists for {employee} for this period.")

    salary_components = employee.salary_components.all().select_related('component')
    
    gross_earnings = Decimal('0.00')
    taxable_earnings = Decimal('0.00')
    non_taxable_earnings = Decimal('0.00')
    pre_tax_deductions = Decimal('0.00')
    post_tax_deductions = Decimal('0.00')
    
    payslip = Payslip.objects.create(
        employee=employee,
        pay_period_start=start_date,
        pay_period_end=end_date,
        status='PENDING'
    )
    
    entries = []
    
    # 1. Calculate Earnings
    earning_comps = salary_components.filter(component__type='EARNING')
    for item in earning_comps:
        gross_earnings += item.amount
        if item.component.is_taxable:
            taxable_earnings += item.amount
        else:
            non_taxable_earnings += item.amount
        
        entries.append(PayslipEntry(
            payslip=payslip,
            component=item.component,
            amount=item.amount
        ))

    # 2. Calculate Statutory Pre-Tax Deductions (NSSA)
    nssa_deduction = calculate_nssa(gross_earnings)
    pre_tax_deductions += nssa_deduction
    
    try:
        nssa_comp = SalaryComponent.objects.get(name__iexact='NSSA')
        entries.append(PayslipEntry(
            payslip=payslip,
            component=nssa_comp,
            amount=nssa_deduction * -1
        ))
    except SalaryComponent.DoesNotExist:
        raise Exception("Statutory component 'NSSA' not found.")

    # 3. Calculate Taxable Income
    taxable_income = taxable_earnings - pre_tax_deductions
    
    # 4. Calculate PAYE and AIDS Levy
    paye_due = calculate_paye(taxable_income)
    aids_levy = (paye_due * AIDS_LEVY_RATE).quantize(Decimal('0.01'))
    total_tax = paye_due + aids_levy
    
    try:
        paye_comp = SalaryComponent.objects.get(name__iexact='PAYE')
        aids_comp = SalaryComponent.objects.get(name__iexact='AIDS Levy')
        entries.append(PayslipEntry(
            payslip=payslip,
            component=paye_comp,
            amount=paye_due * -1
        ))
        entries.append(PayslipEntry(
            payslip=payslip,
            component=aids_comp,
            amount=aids_levy * -1
        ))
    except SalaryComponent.DoesNotExist:
        raise Exception("Statutory components 'PAYE' or 'AIDS Levy' not found.")

    # 5. Calculate other Post-Tax Deductions
    deduction_comps = salary_components.filter(
        component__type='DEDUCTION',
        component__is_statutory=False
    )
    for item in deduction_comps:
        post_tax_deductions += item.amount
        entries.append(PayslipEntry(
            payslip=payslip,
            component=item.component,
            amount=item.amount * -1
        ))

    # 6. Final Calculations
    total_deductions = pre_tax_deductions + total_tax + post_tax_deductions
    net_pay = gross_earnings - total_deductions
    
    # Save all entries
    PayslipEntry.objects.bulk_create(entries)
    
    # Update and save the final payslip
    payslip.gross_earnings = gross_earnings
    payslip.total_deductions = total_deductions
    payslip.net_pay = net_pay
    payslip.status = 'GENERATED'
    payslip.save()
    
    return payslip