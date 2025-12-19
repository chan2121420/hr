from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    User notifications
    """
    class NotificationLevel(models.TextChoices):
        INFO = 'INFO', 'Info'
        SUCCESS = 'SUCCESS', 'Success'
        WARNING = 'WARNING', 'Warning'
        ERROR = 'ERROR', 'Error'
        URGENT = 'URGENT', 'Urgent'

    class NotificationType(models.TextChoices):
        LEAVE = 'LEAVE', 'Leave'
        ATTENDANCE = 'ATTENDANCE', 'Attendance'
        PAYROLL = 'PAYROLL', 'Payroll'
        PERFORMANCE = 'PERFORMANCE', 'Performance'
        TRAINING = 'TRAINING', 'Training'
        ASSET = 'ASSET', 'Asset'
        SYSTEM = 'SYSTEM', 'System'
        RECRUITMENT = 'RECRUITMENT', 'Recruitment'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    level = models.CharField(max_length=10, choices=NotificationLevel.choices, default=NotificationLevel.INFO)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Link to related object
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    
    # Email notification
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
    