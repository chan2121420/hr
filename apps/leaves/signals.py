from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LeaveRequest
from apps.notifications.models import Notification

@receiver(post_save, sender=LeaveRequest)
def create_leave_notification(sender, instance, created, **kwargs):
    if created:
        if instance.employee.manager:
            Notification.objects.create(
                recipient=instance.employee.manager.user,
                message=f"New leave request from {instance.employee} requires your approval.",
                level='INFO'
            )
            
    if not created:
        if instance.status == 'APPROVED':
            Notification.objects.create(
                recipient=instance.employee.user,
                message=f"Your leave request for {instance.start_date} has been approved.",
                level='SUCCESS'
            )
        elif instance.status == 'REJECTED':
             Notification.objects.create(
                recipient=instance.employee.user,
                message=f"Your leave request for {instance.start_date} has been rejected.",
                level='ERROR'
            )