from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PerformanceReview
from apps.notifications.models import Notification

@receiver(post_save, sender=PerformanceReview)
def create_review_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.employee.user,
            message=f"A new performance review for {instance.review_date} has been scheduled.",
            level='INFO'
        )
    
    if instance.status == 'COMPLETED':
        Notification.objects.create(
            recipient=instance.employee.user,
            message=f"Your performance review from {instance.review_date} is complete.",
            level='SUCCESS'
        )