from django.db import models
from apps.core.models import TimeStampedModel
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.employees.models import Employee

class TrainingCategory(TimeStampedModel):
    """Categories of training"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Training Categories'
    
    def __str__(self):
        return self.name

class Course(TimeStampedModel):
    """Training courses"""
    COURSE_TYPES = [
        ('internal', 'Internal Training'),
        ('external', 'External Training'),
        ('online', 'Online Course'),
        ('certification', 'Certification Program'),
    ]
    
    title = models.CharField(max_length=300)
    description = models.TextField()
    category = models.ForeignKey(TrainingCategory, on_delete=models.SET_NULL, null=True, blank=True)
    course_type = models.CharField(max_length=20, choices=COURSE_TYPES)
    
    # Details
    duration_hours = models.DecimalField(max_digits=6, decimal_places=1)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    provider = models.CharField(max_length=200, blank=True)
    instructor = models.CharField(max_length=200, blank=True)
    
    # Content
    objectives = models.TextField()
    prerequisites = models.TextField(blank=True)
    materials = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['title']
    
    def __str__(self):
        return self.title

class TrainingSession(TimeStampedModel):
    """Scheduled training sessions"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=300)
    
    # Schedule
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    meeting_link = models.URLField(blank=True)
    
    # Capacity
    max_participants = models.IntegerField(null=True, blank=True)
    
    # Facilitator
    facilitator = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.title} - {self.start_date.date()}"

class TrainingEnrollment(TimeStampedModel):
    """Employee enrollment in training"""
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_enrollments')
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name='enrollments')
    
    enrolled_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    
    # Completion
    completion_date = models.DateTimeField(null=True, blank=True)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    assessment_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Certificate
    certificate_issued = models.BooleanField(default=False)
    certificate_file = models.FileField(upload_to='training_certificates/', null=True, blank=True)
    
    # Feedback
    feedback = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    class Meta:
        unique_together = ['employee', 'session']
        ordering = ['-enrolled_date']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.session.title}"

class SkillGap(TimeStampedModel):
    """Identified skill gaps"""
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='skill_gaps')
    skill_name = models.CharField(max_length=100)
    current_level = models.CharField(max_length=20, choices=[('none', 'None'), ('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')])
    required_level = models.CharField(max_length=20, choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced'), ('expert', 'Expert')])
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    identified_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    identified_date = models.DateField(auto_now_add=True)
    
    # Development plan
    recommended_courses = models.ManyToManyField(Course, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    
    is_addressed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = 'Skill Gaps'
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.skill_name}"