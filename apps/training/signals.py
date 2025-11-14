from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Enrollment
from apps.notifications.models import Notification

@receiver(post_save, sender=Enrollment)
def create_enrollment_notification(sender, instance, created, **kwargs):
    if created and instance.status == 'ENROLLED':
        Notification.objects.create(
            recipient=instance.employee.user,
            message=f"You have been enrolled in the course: '{instance.session.course.title}' starting on {instance.session.start_date.date()}.",
            level='INFO'
        )