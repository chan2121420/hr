from django.db import models
from apps.core.models import TimeStampedModel

class Notification(TimeStampedModel):
    """System notifications"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('task', 'Task'),
        ('leave', 'Leave'),
        ('approval', 'Approval Required'),
    ]
    
    recipient = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related object (generic)
    related_model = models.CharField(max_length=100, blank=True)
    related_object_id = models.CharField(max_length=100, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Email notification
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"

class EmailTemplate(TimeStampedModel):
    """Email templates for automated emails"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    subject = models.CharField(max_length=300)
    body = models.TextField()  # HTML content with template variables
    
    # Variables available (JSON list)
    available_variables = models.JSONField(default=list)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name