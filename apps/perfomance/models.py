from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee
from decimal import Decimal

class PerformanceMetric(TimeStampedModel):
    """KPIs and performance metrics"""
    METRIC_TYPES = [
        ('quantitative', 'Quantitative'),  # Numerical targets
        ('qualitative', 'Qualitative'),    # Behavioral/Subjective
        ('task_completion', 'Task Completion'),
        ('attendance', 'Attendance'),
        ('customer_satisfaction', 'Customer Satisfaction'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES)
    measurement_unit = models.CharField(max_length=50, blank=True)  # e.g., "sales", "hours", "percentage"
    weight = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.weight}%)"

class PerformanceCycle(TimeStampedModel):
    """Performance review cycles"""
    CYCLE_TYPES = [
        ('annual', 'Annual Review'),
        ('semi_annual', 'Semi-Annual Review'),
        ('quarterly', 'Quarterly Review'),
        ('monthly', 'Monthly Review'),
        ('probation', 'Probation Review'),
    ]
    
    name = models.CharField(max_length=200)
    cycle_type = models.CharField(max_length=20, choices=CYCLE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    review_deadline = models.DateField()
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

class EmployeeGoal(TimeStampedModel):
    """Individual employee goals and objectives"""
    GOAL_TYPES = [
        ('smart', 'SMART Goal'),
        ('okr', 'OKR (Objectives & Key Results)'),
        ('development', 'Development Goal'),
        ('project', 'Project Goal'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='goals')
    cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=300)
    description = models.TextField()
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    metric = models.ForeignKey(PerformanceMetric, on_delete=models.SET_NULL, null=True, blank=True)
    
    # SMART components
    target_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField()
    due_date = models.DateField()
    
    priority = models.CharField(max_length=20, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    completion_percentage = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    set_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='goals_set')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='goals_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', 'due_date']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.title}"
    
    @property
    def progress_percentage(self):
        """Calculate progress based on target vs current value"""
        if self.target_value and self.target_value > 0:
            return min(100, int((self.current_value / self.target_value) * 100))
        return self.completion_percentage
    
    @property
    def is_overdue(self):
        from datetime import date
        return date.today() > self.due_date and self.status != 'completed'

class PerformanceReview(TimeStampedModel):
    """Performance review assessments"""
    REVIEW_TYPES = [
        ('self', 'Self Assessment'),
        ('manager', 'Manager Review'),
        ('peer', 'Peer Review'),
        ('360', '360 Degree Review'),
        ('probation', 'Probation Review'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('completed', 'Completed'),
        ('acknowledged', 'Acknowledged by Employee'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='performance_reviews')
    cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='reviews_conducted')
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPES)
    
    # Overall scores
    overall_rating = models.DecimalField(max_digits=3, decimal_places=1, validators=[MinValueValidator(0), MaxValueValidator(5)], null=True, blank=True)
    
    # Ratings
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    
    # Employee response
    employee_comments = models.TextField(blank=True)
    employee_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['employee', 'cycle', 'review_type', 'reviewer']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.cycle.name} ({self.review_type})"
    
    def calculate_overall_rating(self):
        """Calculate weighted average from metric ratings"""
        ratings = self.metric_ratings.all()
        if not ratings:
            return None
        
        total_weight = sum(r.metric.weight for r in ratings)
        if total_weight == 0:
            return None
        
        weighted_sum = sum(r.rating * r.metric.weight for r in ratings)
        return round(weighted_sum / total_weight, 1)

class MetricRating(TimeStampedModel):
    """Individual metric ratings within a review"""
    review = models.ForeignKey(PerformanceReview, on_delete=models.CASCADE, related_name='metric_ratings')
    metric = models.ForeignKey(PerformanceMetric, on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=1, validators=[MinValueValidator(0), MaxValueValidator(5)])
    comments = models.TextField(blank=True)
    evidence = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['review', 'metric']
    
    def __str__(self):
        return f"{self.metric.name}: {self.rating}/5"

class PerformanceImprovement(TimeStampedModel):
    """Performance Improvement Plans (PIP)"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('successful', 'Successfully Completed'),
        ('unsuccessful', 'Unsuccessful'),
        ('terminated', 'Terminated'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='improvement_plans')
    manager = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='pips_created')
    title = models.CharField(max_length=300)
    
    # Performance issues
    issues_identified = models.TextField()
    expected_improvements = models.TextField()
    
    # Plan details
    start_date = models.DateField()
    end_date = models.DateField()
    review_frequency = models.CharField(max_length=50)  # e.g., "Weekly", "Bi-weekly"
    
    # Support provided
    support_provided = models.TextField()
    training_required = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    final_outcome = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"PIP: {self.employee.get_full_name()} - {self.title}"
