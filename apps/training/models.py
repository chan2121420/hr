from django.db import models
from apps.employees.models import Employee

class TrainingCourse(models.Model):
    """
    Training courses offered
    """
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    provider = models.CharField(max_length=100, blank=True)
    
    duration_hours = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_mandatory = models.BooleanField(default=False)
    is_certification = models.BooleanField(default=False)
    certificate_validity_months = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class CourseSession(models.Model):
    """
    Training course sessions
    """
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name='sessions')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    is_online = models.BooleanField(default=False)
    meeting_link = models.URLField(blank=True)
    
    instructor = models.CharField(max_length=100, blank=True)
    max_participants = models.PositiveIntegerField(default=30)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} ({self.start_date.date()})"


class Enrollment(models.Model):
    """
    Employee course enrollments
    """
    class EnrollmentStatus(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Enrolled'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_enrollments')
    session = models.ForeignKey(CourseSession, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ENROLLED)
    
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    
    certificate_issued = models.BooleanField(default=False)
    certificate_number = models.CharField(max_length=100, blank=True)
    certificate_expiry_date = models.DateField(null=True, blank=True)
    
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'session')

    def __str__(self):
        return f"{self.employee} enrolled in {self.session.course.title}"
