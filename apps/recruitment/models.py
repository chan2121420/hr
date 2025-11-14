from django.db import models
from django.conf import settings
from apps.employees.models import Department, Employee

class JobPosition(models.Model):
    class JobStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    hiring_manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    description = models.TextField()
    requirements = models.TextField()
    status = models.CharField(max_length=10, choices=JobStatus.choices, default=JobStatus.DRAFT)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Candidate(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    resume = models.FileField(upload_to='resumes/')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class Application(models.Model):
    class ApplicationStage(models.TextChoices):
        APPLIED = 'APPLIED', 'Applied'
        SCREENING = 'SCREENING', 'Screening'
        INTERVIEW = 'INTERVIEW', 'Interview'
        OFFER = 'OFFER', 'Offer'
        HIRED = 'HIRED', 'Hired'
        REJECTED = 'REJECTED', 'Rejected'

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(JobPosition, on_delete=models.CASCADE, related_name='applications')
    stage = models.CharField(max_length=20, choices=ApplicationStage.choices, default=ApplicationStage.APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.candidate} for {self.job.title}"

class Interview(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interviewers = models.ManyToManyField(Employee, related_name='interviews_conducted')
    scheduled_at = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Interview for {self.application}"