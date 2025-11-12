from django.db import models
from apps.core.models import TimeStampedModel
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.employees.models import Position

class JobPosting(TimeStampedModel):
    """Job vacancy postings"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
    ]
    
    title = models.CharField(max_length=300)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='job_postings')
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField()
    
    # Employment details
    employment_type = models.CharField(max_length=20)
    salary_range_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_range_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vacancies = models.IntegerField(default=1)
    
    # Posting details
    posted_date = models.DateField(auto_now_add=True)
    closing_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Location
    location = models.CharField(max_length=200)
    remote_option = models.BooleanField(default=False)
    
    posted_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-posted_date']
    
    def __str__(self):
        return f"{self.title} - {self.position.department.name}"

class Candidate(TimeStampedModel):
    """Job applicants"""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    
    # Documents
    cv = models.FileField(upload_to='candidate_cvs/')
    cover_letter = models.TextField(blank=True)
    
    # Experience
    years_of_experience = models.IntegerField(null=True, blank=True)
    current_employer = models.CharField(max_length=200, blank=True)
    current_position = models.CharField(max_length=200, blank=True)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Source
    source = models.CharField(max_length=100, default='Website')  # LinkedIn, Referral, etc.
    referrer = models.CharField(max_length=200, blank=True)
    
    # Blacklist
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Application(TimeStampedModel):
    """Job applications"""
    STATUS_CHOICES = [
        ('received', 'Application Received'),
        ('screening', 'Under Screening'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('offer', 'Offer Extended'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    application_date = models.DateTimeField(auto_now_add=True)
    
    # Screening
    screening_score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    screened_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='applications_screened')
    screening_notes = models.TextField(blank=True)
    
    # Overall assessment
    overall_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    
    class Meta:
        unique_together = ['job_posting', 'candidate']
        ordering = ['-application_date']
    
    def __str__(self):
        return f"{self.candidate} - {self.job_posting.title}"

class Interview(TimeStampedModel):
    """Interview schedules"""
    INTERVIEW_TYPES = [
        ('phone', 'Phone Screening'),
        ('video', 'Video Interview'),
        ('in_person', 'In-Person Interview'),
        ('technical', 'Technical Assessment'),
        ('hr', 'HR Interview'),
        ('final', 'Final Interview'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
        ('no_show', 'No Show'),
    ]
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES)
    
    # Schedule
    scheduled_date = models.DateTimeField()
    duration = models.IntegerField(default=60)  # minutes
    location = models.CharField(max_length=200, blank=True)
    meeting_link = models.URLField(blank=True)
    
    # Interviewers
    interviewers = models.ManyToManyField('accounts.User', related_name='interviews_conducting')
    
    # Status and feedback
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField(blank=True)
    
    # Notes
    questions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.application.candidate} - {self.interview_type} on {self.scheduled_date}"

class Onboarding(TimeStampedModel):
    """Employee onboarding process"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    employee = models.OneToOneField('employees.Employee', on_delete=models.CASCADE, related_name='onboarding')
    application = models.OneToOneField(Application, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Dates
    start_date = models.DateField()
    expected_completion_date = models.DateField()
    actual_completion_date = models.DateField(null=True, blank=True)
    
    # Buddy/Mentor
    buddy = models.ForeignKey('employees.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='onboarding_buddies')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    completion_percentage = models.IntegerField(default=0)
    
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Onboarding: {self.employee.get_full_name()}"

class OnboardingTask(TimeStampedModel):
    """Tasks in onboarding checklist"""
    onboarding = models.ForeignKey(Onboarding, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    due_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'due_date']
    
    def __str__(self):
        return self.title
