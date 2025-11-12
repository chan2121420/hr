
from django.db import models
from apps.core.models import TimeStampedModel

class DashboardWidget(TimeStampedModel):
    """Configurable dashboard widgets"""
    WIDGET_TYPES = [
        ('kpi_card', 'KPI Card'),
        ('chart_line', 'Line Chart'),
        ('chart_bar', 'Bar Chart'),
        ('chart_pie', 'Pie Chart'),
        ('table', 'Data Table'),
        ('list', 'List'),
    ]
    
    name = models.CharField(max_length=200)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    data_source = models.CharField(max_length=100)  # Model or query name
    configuration = models.JSONField(default=dict)  # Widget-specific settings
    refresh_interval = models.IntegerField(default=300)  # Seconds
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.name

class Report(TimeStampedModel):
    """Saved reports"""
    REPORT_TYPES = [
        ('employee', 'Employee Report'),
        ('attendance', 'Attendance Report'),
        ('leave', 'Leave Report'),
        ('payroll', 'Payroll Report'),
        ('performance', 'Performance Report'),
        ('task', 'Task Report'),
        ('custom', 'Custom Report'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    
    # Filters and parameters
    filters = models.JSONField(default=dict)
    columns = models.JSONField(default=list)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
