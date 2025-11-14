from django.db import models
from apps.employees.models import Employee

class TrainingCourse(models.Model):
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    provider = models.CharField(max_length=100, blank=True) # e.g., NSSA, Internal
    
    def __str__(self):
        return self.title

class CourseSession(models.Model):
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name='sessions')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    instructor = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.course.title} ({self.start_date.date()})"

class Enrollment(models.Model):
    class EnrollmentStatus(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Enrolled'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_enrollments')
    session = models.ForeignKey(CourseSession, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ENROLLED)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('employee', 'session')

    def __str__(self):
        return f"{self.employee} enrolled in {self.session.course.title}"