from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from .models import LeaveRequest, LeaveBalance, LeaveType, Holiday
from apps.notifications.models import Notification
from apps.employees.models import Employee


@receiver(pre_save, sender=LeaveRequest)
def validate_leave_request_before_save(sender, instance, **kwargs):
    """Validate leave request before saving"""
    if instance.pk:
        # Get old instance to compare status changes
        try:
            old_instance = LeaveRequest.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except LeaveRequest.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender=LeaveRequest)
def handle_leave_request_changes(sender, instance, created, **kwargs):
    """Handle leave request creation and status changes"""
    old_status = getattr(instance, '_old_status', None)
    
    if created:
        # New leave request created
        _handle_new_leave_request(instance)
        _update_balance_for_new_request(instance)
    else:
        # Status changed
        if old_status and old_status != instance.status:
            _handle_status_change(instance, old_status)
            _send_status_notification(instance, old_status)


def _handle_new_leave_request(leave_request):
    """Handle new leave request notifications"""
    employee = leave_request.employee
    
    # Notify manager
    if employee.manager:
        Notification.objects.create(
            recipient=employee.manager.user,
            title="New Leave Request",
            message=f"{employee.full_name} has requested {leave_request.leave_type.name} "
                   f"from {leave_request.start_date} to {leave_request.end_date}",
            notification_type='LEAVE_REQUEST',
            related_object_id=str(leave_request.id),
            level='INFO',
            action_url=f'/leaves/requests/{leave_request.id}/'
        )
    
    # Notify HR if required
    if leave_request.leave_type.requires_hr_approval:
        _notify_hr_users(leave_request, "New Leave Request Requiring HR Approval")
    
    # Notify covering employee if assigned
    if leave_request.covering_employee:
        Notification.objects.create(
            recipient=leave_request.covering_employee.user,
            title="Leave Coverage Request",
            message=f"{employee.full_name} has requested you to cover their work "
                   f"from {leave_request.start_date} to {leave_request.end_date}",
            notification_type='LEAVE_COVERAGE',
            related_object_id=str(leave_request.id),
            level='INFO',
            action_url=f'/leaves/requests/{leave_request.id}/'
        )
        leave_request.covering_employee_notified = True
        LeaveRequest.objects.filter(pk=leave_request.pk).update(
            covering_employee_notified=True
        )


def _handle_status_change(leave_request, old_status):
    """Handle leave request status changes"""
    if leave_request.status == 'APPROVED' and old_status != 'APPROVED':
        # Leave approved
        _send_approval_notification(leave_request)
        _create_calendar_reminder(leave_request)
        
    elif leave_request.status == 'REJECTED':
        # Leave rejected
        _send_rejection_notification(leave_request)
        
    elif leave_request.status in ['CANCELLED', 'WITHDRAWN']:
        # Leave cancelled or withdrawn
        _send_cancellation_notification(leave_request, old_status)
        _notify_affected_parties(leave_request)


def _update_balance_for_new_request(leave_request):
    """Update leave balance when new request is created"""
    if leave_request.status == 'PENDING':
        year = leave_request.start_date.year
        
        try:
            balance = LeaveBalance.objects.select_for_update().get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=year
            )
            
            days = Decimal(str(leave_request.total_leave_days))
            balance.pending += days
            balance.save(update_fields=['pending', 'updated_at'])
            
        except LeaveBalance.DoesNotExist:
            # Create balance if it doesn't exist
            LeaveBalance.objects.create(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=year,
                total_allocated=leave_request.leave_type.default_days_allocated,
                pending=Decimal(str(leave_request.total_leave_days))
            )


def _send_status_notification(leave_request, old_status):
    """Send notification based on status change"""
    employee = leave_request.employee
    
    if leave_request.status == 'MANAGER_APPROVED':
        # Notify employee
        Notification.objects.create(
            recipient=employee.user,
            title="Leave Request Approved by Manager",
            message=f"Your {leave_request.leave_type.name} request has been approved by your manager. "
                   f"{'Waiting for HR approval.' if leave_request.leave_type.requires_hr_approval else 'Your leave is confirmed.'}",
            notification_type='LEAVE_APPROVED',
            related_object_id=str(leave_request.id),
            level='SUCCESS',
            action_url=f'/leaves/requests/{leave_request.id}/'
        )
        
        # Notify HR if required
        if leave_request.leave_type.requires_hr_approval:
            _notify_hr_users(leave_request, "Leave Request Requires HR Approval")


def _send_approval_notification(leave_request):
    """Send notification when leave is fully approved"""
    Notification.objects.create(
        recipient=leave_request.employee.user,
        title="Leave Request Approved",
        message=f"Your {leave_request.leave_type.name} from {leave_request.start_date} "
               f"to {leave_request.end_date} has been approved.",
        notification_type='LEAVE_APPROVED',
        related_object_id=str(leave_request.id),
        level='SUCCESS',
        action_url=f'/leaves/requests/{leave_request.id}/',
        is_actionable=False
    )
    
    # Mark employee as notified
    LeaveRequest.objects.filter(pk=leave_request.pk).update(employee_notified=True)


def _send_rejection_notification(leave_request):
    """Send notification when leave is rejected"""
    Notification.objects.create(
        recipient=leave_request.employee.user,
        title="Leave Request Rejected",
        message=f"Your {leave_request.leave_type.name} request has been rejected. "
               f"Reason: {leave_request.rejection_reason or 'No reason provided'}",
        notification_type='LEAVE_REJECTED',
        related_object_id=str(leave_request.id),
        level='ERROR',
        action_url=f'/leaves/requests/{leave_request.id}/'
    )


def _send_cancellation_notification(leave_request, old_status):
    """Send notification when leave is cancelled or withdrawn"""
    if leave_request.status == 'CANCELLED':
        Notification.objects.create(
            recipient=leave_request.employee.user,
            title="Leave Request Cancelled",
            message=f"Your {leave_request.leave_type.name} has been cancelled. "
                   f"Reason: {leave_request.cancellation_reason or 'No reason provided'}",
            notification_type='LEAVE_CANCELLED',
            related_object_id=str(leave_request.id),
            level='WARNING',
            action_url=f'/leaves/requests/{leave_request.id}/'
        )
    elif leave_request.status == 'WITHDRAWN':
        # Notify manager if the request was pending
        if old_status == 'PENDING' and leave_request.employee.manager:
            Notification.objects.create(
                recipient=leave_request.employee.manager.user,
                title="Leave Request Withdrawn",
                message=f"{leave_request.employee.full_name} has withdrawn their leave request.",
                notification_type='LEAVE_WITHDRAWN',
                related_object_id=str(leave_request.id),
                level='INFO'
            )


def _notify_affected_parties(leave_request):
    """Notify affected parties about leave cancellation"""
    # Notify covering employee
    if leave_request.covering_employee:
        Notification.objects.create(
            recipient=leave_request.covering_employee.user,
            title="Leave Coverage Cancelled",
            message=f"{leave_request.employee.full_name}'s leave has been cancelled. "
                   f"You are no longer required to cover.",
            notification_type='LEAVE_CANCELLED',
            related_object_id=str(leave_request.id),
            level='INFO'
        )
    
    # Notify manager
    if leave_request.employee.manager:
        Notification.objects.create(
            recipient=leave_request.employee.manager.user,
            title="Team Leave Cancelled",
            message=f"{leave_request.employee.full_name}'s leave from "
                   f"{leave_request.start_date} has been cancelled.",
            notification_type='LEAVE_CANCELLED',
            related_object_id=str(leave_request.id),
            level='INFO'
        )


def _create_calendar_reminder(leave_request):
    """Create reminder notifications for upcoming leave"""
    # Reminder 3 days before leave starts
    if leave_request.days_until_start and leave_request.days_until_start > 3:
        # Schedule reminder (you'd need a task scheduler like Celery for this)
        # For now, we'll create a placeholder notification
        pass


def _notify_hr_users(leave_request, title):
    """Notify all HR users"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Get HR users (adjust based on your permission structure)
    hr_users = User.objects.filter(
        groups__name__in=['HR', 'HR Manager', 'HR Admin']
    ).distinct()
    
    for hr_user in hr_users:
        Notification.objects.create(
            recipient=hr_user,
            title=title,
            message=f"{leave_request.employee.full_name} has requested {leave_request.leave_type.name} "
                   f"from {leave_request.start_date} to {leave_request.end_date}",
            notification_type='LEAVE_REQUEST',
            related_object_id=str(leave_request.id),
            level='INFO',
            action_url=f'/leaves/requests/{leave_request.id}/'
        )


@receiver(post_save, sender=LeaveBalance)
def notify_low_balance(sender, instance, created, **kwargs):
    """Notify employee when leave balance is low"""
    if not created:
        # Check if balance is low (less than 3 days)
        if instance.available > 0 and instance.available <= 3:
            # Check if we've already notified recently
            recent_notification = Notification.objects.filter(
                recipient=instance.employee.user,
                notification_type='LOW_LEAVE_BALANCE',
                created_at__gte=timezone.now() - timedelta(days=30)
            ).exists()
            
            if not recent_notification:
                Notification.objects.create(
                    recipient=instance.employee.user,
                    title="Low Leave Balance",
                    message=f"Your {instance.leave_type.name} balance is low: "
                           f"{instance.available} days remaining",
                    notification_type='LOW_LEAVE_BALANCE',
                    level='WARNING',
                    action_url='/leaves/balances/'
                )


@receiver(post_save, sender=Employee)
def initialize_employee_leave_balances(sender, instance, created, **kwargs):
    """Initialize leave balances for new employees"""
    if created and instance.status == 'ACTIVE':
        current_year = date.today().year
        active_leave_types = LeaveType.objects.filter(is_active=True)
        
        for leave_type in active_leave_types:
            # Check eligibility
            is_eligible, _ = leave_type.is_eligible(instance)
            
            if is_eligible:
                LeaveBalance.objects.get_or_create(
                    employee=instance,
                    leave_type=leave_type,
                    year=current_year,
                    defaults={
                        'total_allocated': leave_type.default_days_allocated
                    }
                )

@receiver(post_delete, sender=LeaveRequest)
def cleanup_leave_balance_on_delete(sender, instance, **kwargs):
    """Clean up leave balance when request is deleted"""
    if instance.status == 'PENDING':
        year = instance.start_date.year
        try:
            balance = LeaveBalance.objects.get(
                employee=instance.employee,
                leave_type=instance.leave_type,
                year=year
            )
            days = Decimal(str(instance.total_leave_days))
            balance.pending -= days
            balance.save(update_fields=['pending', 'updated_at'])
        except LeaveBalance.DoesNotExist:
            pass