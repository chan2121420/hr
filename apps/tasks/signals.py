from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
from apps.notifications.models import Notification

@receiver(post_save, sender=Task)
def create_task_notification(sender, instance, created, **kwargs):
    if created and instance.assigned_to:
        Notification.objects.create(
            recipient=instance.assigned_to.user,
            title="New Task Assigned",
            message=f"You have been assigned a new task: {instance.title}",
            notification_type='SYSTEM', # or TASK if available
            action_url=f"/tasks/my-tasks/" 
        )