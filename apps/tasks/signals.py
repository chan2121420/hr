from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
from apps.notifications.models import Notification

@receiver(post_save, sender=Task)
def create_task_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.assigned_to.user,
            message=f"New task assigned to you: '{instance.title}'",
            level='INFO'
        )