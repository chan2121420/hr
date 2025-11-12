from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee

class TaskCategory(TimeStampedModel):
    """Task categories for organization"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3B82F6')  # Hex color code
    icon = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name_plural = 'Task Categories'
    
    def __str__(self):
        return self.name

class Task(TimeStampedModel):
    """Main task model with performance-based allocation"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=300)
    description = models.TextField()
    category = models.ForeignKey(TaskCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    
    # Assignment
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assigned_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='tasks_assigned')
    department = models.ForeignKey('core.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    
    # Priority and Status
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timing
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Progress
    completion_percentage = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Performance Metrics
    difficulty_level = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])  # 1=Very Easy, 5=Very Hard
    quality_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    
    # Dependencies
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependent_tasks')
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_tasks')
    
    # Review
    reviewed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks_reviewed')
    review_comments = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', 'due_date']
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status', 'priority']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_overdue(self):
        from datetime import date
        return date.today() > self.due_date and self.status not in ['completed', 'cancelled']
    
    @property
    def days_until_due(self):
        from datetime import date
        delta = self.due_date - date.today()
        return delta.days
    
    def calculate_performance_score(self):
        """Calculate task performance score based on completion time, quality, etc."""
        if self.status != 'completed' or not self.completed_at:
            return None
        
        score = 100
        
        # Deduct points for being late
        if self.completed_at.date() > self.due_date:
            days_late = (self.completed_at.date() - self.due_date).days
            score -= min(days_late * 5, 30)  # Max 30 points deduction
        
        # Bonus for early completion
        elif self.completed_at.date() < self.due_date:
            days_early = (self.due_date - self.completed_at.date()).days
            score += min(days_early * 2, 10)  # Max 10 points bonus
        
        # Quality score impact
        if self.quality_score:
            quality_impact = (self.quality_score - 3) * 5  # -10 to +10
            score += quality_impact
        
        return max(0, min(100, score))  # Clamp between 0 and 100

class TaskComment(TimeStampedModel):
    """Comments and updates on tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='task_comments')
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal notes vs visible to assignee
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment on {self.task.title} by {self.user.username}"

class TaskAttachment(TimeStampedModel):
    """File attachments for tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/%Y/%m/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.filename

class TaskAllocationRule(TimeStampedModel):
    """Rules for automatic task allocation based on performance"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    # Criteria
    department = models.ForeignKey('core.Department', on_delete=models.CASCADE, null=True, blank=True)
    min_performance_rating = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)
    max_concurrent_tasks = models.IntegerField(default=5)
    required_skills = models.JSONField(default=list, blank=True)  # List of required skills
    
    # Task matching
    task_categories = models.ManyToManyField(TaskCategory, blank=True)
    max_difficulty_level = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    priority = models.IntegerField(default=1)  # Higher number = higher priority
    
    class Meta:
        ordering = ['-priority']
    
    def __str__(self):
        return self.name

class EmployeeTaskPerformance(TimeStampedModel):
    """Aggregate task performance metrics per employee"""
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='task_performance')
    
    # Task Statistics
    total_tasks_assigned = models.IntegerField(default=0)
    total_tasks_completed = models.IntegerField(default=0)
    tasks_completed_on_time = models.IntegerField(default=0)
    tasks_completed_late = models.IntegerField(default=0)
    tasks_in_progress = models.IntegerField(default=0)
    
    # Performance Metrics
    average_completion_time = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # In days
    average_quality_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    overall_performance_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # 0-100
    
    # Current Workload
    current_task_count = models.IntegerField(default=0)
    current_workload_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Ratings
    reliability_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)  # 0-5
    efficiency_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)  # 0-5
    
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Employee Task Performances'
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - Performance Score: {self.overall_performance_score}"
    
    def calculate_metrics(self):
        """Recalculate all performance metrics"""
        completed_tasks = Task.objects.filter(
            assigned_to=self.employee,
            status='completed'
        )
        
        self.total_tasks_completed = completed_tasks.count()
        self.tasks_completed_on_time = completed_tasks.filter(
            completed_at__date__lte=models.F('due_date')
        ).count()
        self.tasks_completed_late = self.total_tasks_completed - self.tasks_completed_on_time
        
        # Calculate average quality score
        quality_scores = completed_tasks.exclude(quality_score__isnull=True).values_list('quality_score', flat=True)
        if quality_scores:
            self.average_quality_score = sum(quality_scores) / len(quality_scores)
        
        # Calculate reliability (on-time completion rate)
        if self.total_tasks_completed > 0:
            self.reliability_score = (self.tasks_completed_on_time / self.total_tasks_completed) * 5
        
        # Calculate overall performance score
        scores = []
        if self.reliability_score:
            scores.append(self.reliability_score * 20)  # Convert to 0-100 scale
        if self.average_quality_score:
            scores.append(self.average_quality_score * 20)  # Convert to 0-100 scale
        
        if scores:
            self.overall_performance_score = sum(scores) / len(scores)
        
        # Current workload
        self.current_task_count = Task.objects.filter(
            assigned_to=self.employee,
            status__in=['assigned', 'in_progress']
        ).count()
        
        self.save()

class TaskTemplate(TimeStampedModel):
    """Reusable task templates"""
    title = models.CharField(max_length=300)
    description = models.TextField()
    category = models.ForeignKey(TaskCategory, on_delete=models.SET_NULL, null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    difficulty_level = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    required_skills = models.JSONField(default=list, blank=True)
    checklist = models.JSONField(default=list, blank=True)  # List of subtasks
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title