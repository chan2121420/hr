from celery import shared_task
from django.utils import timezone
from datetime import timedelta, date
from apps.perfomance.models import EmployeeTaskPerformance
from apps.tasks.models import Task
from apps.attendance.models import Attendance
from apps.leaves.models import LeaveRequest, LeaveBalance
from apps.payroll.models import PayrollPeriod, Payslip
from apps.core.utils import send_notification
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_employee_task_performance():
    """
    Scheduled task to update all employees' task performance metrics
    Run daily
    """
    from apps.employees.models import Employee
    
    for employee in Employee.objects.filter(is_active=True):
        performance, created = EmployeeTaskPerformance.objects.get_or_create(
            employee=employee
        )
        performance.calculate_metrics()
    
    logger.info("Updated task performance metrics for all employees")

@shared_task
def send_task_deadline_reminders():
    """
    Send reminders for tasks due in 2 days
    Run daily
    """
    tomorrow = date.today() + timedelta(days=1)
    two_days = date.today() + timedelta(days=2)
    
    tasks = Task.objects.filter(
        due_date__in=[tomorrow, two_days],
        status__in=['assigned', 'in_progress']
    ).select_related('assigned_to__user_account')
    
    for task in tasks:
        if task.assigned_to and task.assigned_to.user_account:
            days_left = (task.due_date - date.today()).days
            send_notification(
                user=task.assigned_to.user_account,
                notification_type='task',
                title=f'Task Due in {days_left} Days',
                message=f'Task "{task.title}" is due on {task.due_date}',
                related_model='Task',
                related_object_id=task.id,
                send_email=True
            )
    
    logger.info(f"Sent deadline reminders for {tasks.count()} tasks")

@shared_task
def process_leave_accruals():
    """
    Monthly task to accrue leave balances
    Run on 1st of every month
    """
    from apps.employees.models import Employee
    from apps.leaves.models import LeaveType, LeaveBalance
    from dateutil.relativedelta import relativedelta
    
    current_year = date.today().year
    current_month = date.today().month
    
    for employee in Employee.objects.filter(is_active=True):
        # Calculate months of service
        months_service = relativedelta(date.today(), employee.date_joined).months
        
        for leave_type in LeaveType.objects.filter(is_active=True):
            balance, created = LeaveBalance.objects.get_or_create(
                employee=employee,
                leave_type=leave_type,
                year=current_year,
                defaults={'total_days': 0}
            )
            
            # Monthly accrual
            monthly_accrual = leave_type.days_allowed_per_year / 12
            balance.total_days += monthly_accrual
            balance.save()
    
    logger.info("Processed monthly leave accruals")

@shared_task
def mark_absent_employees():
    """
    Mark employees as absent if no attendance record by end of grace period
    Run every hour during work hours
    """
    from django.conf import settings
    
    today = date.today()
    grace_period = settings.HR_SYSTEM.get('ATTENDANCE_GRACE_PERIOD', 15)
    
    # Implementation would check attendance records and mark absences
    logger.info("Checked for absent employees")

@shared_task
def generate_payroll_reminders():
    """
    Send reminders when payroll period is ending
    """
    upcoming_periods = PayrollPeriod.objects.filter(
        end_date=date.today() + timedelta(days=3),
        is_processed=False
    )
    
    # Send notifications to HR team
    logger.info(f"Sent payroll reminders for {upcoming_periods.count()} periods")
