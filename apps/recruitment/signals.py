from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Application
from apps.notifications.models import Notification

@receiver(post_save, sender=Application)
def create_application_notification(sender, instance, created, **kwargs):
    if created:
        job = instance.job
        if job.hiring_manager:
            Notification.objects.create(
                recipient=job.hiring_manager.user,
                message=f"New application from {instance.candidate} for {job.title}.",
                level='INFO'
            )