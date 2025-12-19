
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from apps.employees.models import Employee
from decimal import Decimal


class PerformanceMetric(models.Model):
    """
    Define performance metrics for evaluation
    """
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=[
            ('PRODUCTIVITY', 'Productivity'),
            ('QUALITY', 'Quality'),
            ('TEAMWORK', 'Teamwork'),
            ('LEADERSHIP', 'Leadership'),
            ('COMMUNICATION', 'Communication'),
            ('INNOVATION', 'Innovation'),
            ('ATTENDANCE', 'Attendance'),
            ('TECHNICAL', 'Technical Skills'),
        ]
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1,
        help_text="Weight in overall performance score"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Goal(models.Model):
    """
    Employee goals and objectives
    """
    class GoalStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        CANCELLED = 'CANCELLED', 'Cancelled'
        OVERDUE = 'OVERDUE', 'Overdue'

    class GoalPriority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    category = models.CharField(
        max_length=50,
        choices=[
            ('PERSONAL', 'Personal Development'),
            ('DEPARTMENTAL', 'Departmental'),
            ('ORGANIZATIONAL', 'Organizational'),
            ('SKILL_DEVELOPMENT', 'Skill Development'),
            ('PROJECT', 'Project-based'),
        ],
        default='PERSONAL'
    )
    
    start_date = models.DateField()
    due_date = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=GoalStatus.choices, default=GoalStatus.ACTIVE)
    priority = models.CharField(max_length=20, choices=GoalPriority.choices, default=GoalPriority.MEDIUM)
    
    # Progress tracking
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Metrics and KPIs
    target_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    measurement_unit = models.CharField(max_length=50, blank=True)
    
    # Assignment
    set_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='goals_set'
    )
    
    # Support and resources
    required_resources = models.TextField(blank=True)
    support_needed = models.TextField(blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date', 'priority']

    def __str__(self):
        return f"{self.title} ({self.employee})"

    @property
    def is_overdue(self):
        from datetime import date
        return self.status == 'ACTIVE' and self.due_date < date.today()

    @property
    def achievement_percentage(self):
        if self.target_value and self.actual_value:
            return min(100, int((self.actual_value / self.target_value) * 100))
        return self.progress_percentage


class PerformanceReview(models.Model):
    """
    Comprehensive performance reviews
    """
    class ReviewType(models.TextChoices):
        PROBATION = 'PROBATION', 'Probation Review'
        QUARTERLY = 'QUARTERLY', 'Quarterly Review'
        ANNUAL = 'ANNUAL', 'Annual Review'
        MID_YEAR = 'MID_YEAR', 'Mid-Year Review'
        PROJECT = 'PROJECT', 'Project Review'
        ADHOC = 'ADHOC', 'Ad-hoc Review'

    class ReviewStatus(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SELF_ASSESSMENT = 'SELF_ASSESSMENT', 'Self Assessment'
        MANAGER_REVIEW = 'MANAGER_REVIEW', 'Manager Review'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews_conducted'
    )
    
    review_type = models.CharField(max_length=20, choices=ReviewType.choices)
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    review_date = models.DateField()
    
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.SCHEDULED)
    
    # Overall ratings
    overall_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Overall rating from 1 (Poor) to 5 (Excellent)"
    )
    
    # Self assessment
    self_assessment_completed = models.BooleanField(default=False)
    self_assessment_date = models.DateField(null=True, blank=True)
    self_assessment_comments = models.TextField(blank=True)
    self_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    # Manager assessment
    manager_comments = models.TextField(blank=True, null=True)
    manager_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    # Detailed assessments
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    challenges_faced = models.TextField(blank=True)
    
    # Development plan
    development_plan = models.TextField(blank=True)
    training_recommendations = models.TextField(blank=True)
    career_aspirations = models.TextField(blank=True)
    
    # Goals
    goals_discussed = models.ManyToManyField(Goal, blank=True, related_name='reviews')
    goals_achieved = models.PositiveIntegerField(default=0)
    goals_total = models.PositiveIntegerField(default=0)
    
    # Compensation and promotions
    salary_adjustment_recommended = models.BooleanField(default=False)
    salary_adjustment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    promotion_recommended = models.BooleanField(default=False)
    promotion_position = models.CharField(max_length=200, blank=True)
    
    # Action items
    action_items = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Signatures/acknowledgment
    employee_acknowledged = models.BooleanField(default=False)
    employee_acknowledged_at = models.DateTimeField(null=True, blank=True)
    employee_signature = models.TextField(blank=True)
    employee_comments = models.TextField(blank=True)
    
    reviewer_signed = models.BooleanField(default=False)
    reviewer_signed_at = models.DateTimeField(null=True, blank=True)
    
    # Attachments
    supporting_documents = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-review_date', 'employee']

    def __str__(self):
        return f"{self.review_type} Review for {self.employee} on {self.review_date}"

    @property
    def goal_achievement_rate(self):
        if self.goals_total > 0:
            return (self.goals_achieved / self.goals_total) * 100
        return 0


class PerformanceImprovement(models.Model):
    """
    Performance Improvement Plans (PIP)
    """
    class PIPStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Successfully Completed'
        EXTENDED = 'EXTENDED', 'Extended'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='improvement_plans')
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_pips'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    start_date = models.DateField()
    end_date = models.DateField()
    review_frequency_days = models.PositiveIntegerField(default=14)
    
    status = models.CharField(max_length=20, choices=PIPStatus.choices, default=PIPStatus.ACTIVE)
    
    # Issues
    performance_issues = models.TextField()
    expected_improvements = models.TextField()
    success_criteria = models.TextField()
    
    # Support
    support_provided = models.TextField()
    resources_allocated = models.TextField(blank=True)
    training_required = models.TextField(blank=True)
    
    # Progress tracking
    progress_notes = models.TextField(blank=True)
    milestones_achieved = models.TextField(blank=True)
    
    # Outcome
    outcome = models.TextField(blank=True)
    final_recommendation = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PIP: {self.employee} - {self.title}"