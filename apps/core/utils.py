from datetime import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from apps.notifications.models import Notification, EmailTemplate
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def send_notification(user, notification_type, title, message, related_model=None, related_object_id=None, action_url=None, send_email=False):
    """
    Create and optionally email a notification to a user
    """
    notification = Notification.objects.create(
        recipient=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_model=related_model or '',
        related_object_id=str(related_object_id) if related_object_id else '',
        action_url=action_url or ''
    )
    
    if send_email and user.email:
        try:
            send_mail(
                subject=title,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save()
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    return notification

def calculate_paye_tax(gross_salary):
    """
    Calculate Zimbabwe PAYE tax
    Tax bands as of 2024 (update as needed):
    - Up to $600: 0%
    - $600 - $1,200: 20%
    - $1,200 - $1,800: 25%
    - Above $1,800: 30%
    """
    tax = Decimal('0')
    
    if gross_salary <= 600:
        tax = Decimal('0')
    elif gross_salary <= 1200:
        tax = (gross_salary - 600) * Decimal('0.20')
    elif gross_salary <= 1800:
        tax = (600 * Decimal('0.20')) + ((gross_salary - 1200) * Decimal('0.25'))
    else:
        tax = (600 * Decimal('0.20')) + (600 * Decimal('0.25')) + ((gross_salary - 1800) * Decimal('0.30'))
    
    return tax.quantize(Decimal('0.01'))

def calculate_nssa(basic_salary):
    """
    Calculate NSSA contributions for Zimbabwe
    Employee: 3.5% of basic salary
    Employer: 3.5% of basic salary
    Maximum monthly contribution: based on max insurable earnings
    """
    rate = Decimal('0.035')
    max_insurable = Decimal('700')  # Update as per current NSSA regulations
    
    insurable_amount = min(basic_salary, max_insurable)
    employee_contribution = (insurable_amount * rate).quantize(Decimal('0.01'))
    employer_contribution = (insurable_amount * rate).quantize(Decimal('0.01'))
    
    return {
        'employee': employee_contribution,
        'employer': employer_contribution
    }

def calculate_working_days(start_date, end_date, exclude_weekends=True):
    """Calculate number of working days between two dates"""
    from datetime import timedelta
    from apps.attendance.models import Holiday
    
    days = 0
    current_date = start_date
    holidays = set(Holiday.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).values_list('date', flat=True))
    
    while current_date <= end_date:
        is_weekend = exclude_weekends and current_date.weekday() >= 5
        is_holiday = current_date in holidays
        
        if not is_weekend and not is_holiday:
            days += 1
        
        current_date += timedelta(days=1)
    
    return days

def allocate_task_to_best_employee(task):
    """
    Intelligent task allocation based on employee performance
    """
    from apps.tasks.models import EmployeeTaskPerformance, TaskAllocationRule
    from apps.employees.models import Employee
    
    # Get applicable allocation rules
    rules = TaskAllocationRule.objects.filter(
        is_active=True,
        department=task.department
    ).order_by('-priority')
    
    if not rules.exists():
        return None
    
    rule = rules.first()
    
    # Find eligible employees
    eligible_employees = Employee.objects.filter(
        department=task.department,
        is_active=True
    )
    
    # Get their performance metrics
    performances = EmployeeTaskPerformance.objects.filter(
        employee__in=eligible_employees,
        overall_performance_score__gte=rule.min_performance_rating * 20,  # Convert to 0-100 scale
        current_task_count__lt=rule.max_concurrent_tasks
    ).select_related('employee').order_by('-overall_performance_score')
    
    if performances.exists():
        # Allocate to best performing employee with capacity
        best_employee = performances.first().employee
        task.assigned_to = best_employee
        task.status = 'assigned'
        task.save()
        
        # Update workload
        performance = performances.first()
        performance.current_task_count += 1
        if task.estimated_hours:
            performance.current_workload_hours += task.estimated_hours
        performance.save()
        
        return best_employee
    
    return None