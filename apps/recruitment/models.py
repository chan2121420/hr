from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.employees.models import Department, Employee

class JobPosition(models.Model):
    """
    Job openings and positions
    """
    class JobStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        CLOSED = 'CLOSED', 'Closed'
        FILLED = 'FILLED', 'Filled'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class JobType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full-Time'
        PART_TIME = 'PART_TIME', 'Part-Time'
        CONTRACT = 'CONTRACT', 'Contract'
        INTERN = 'INTERN', 'Internship'

    title = models.CharField(max_length=200)
    job_code = models.CharField(max_length=50, unique=True, blank=True)
    department = models.ForeignKey(
        'employees.Department',
        on_delete=models.SET_NULL,
        null=True
    )
    designation = models.ForeignKey(
        'employees.Designation',
        on_delete=models.SET_NULL,
        null=True
    )
    
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField()
    
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    location = models.CharField(max_length=200)
    
    # Salary range
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='USD')
    
    # Requirements
    required_experience_years = models.PositiveIntegerField(default=0)
    required_education = models.TextField(blank=True)
    required_skills = models.TextField(blank=True)
    
    # Vacancy details
    number_of_positions = models.PositiveIntegerField(default=1)
    positions_filled = models.PositiveIntegerField(default=0)
    
    hiring_manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.DRAFT)
    
    posted_at = models.DateTimeField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    
    is_internal_only = models.BooleanField(default=False)
    is_remote = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_jobs'
    )

    def __str__(self):
        return self.title


class Candidate(models.Model):
    """
    Job candidates
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    
    # Documents
    resume = models.FileField(upload_to='resumes/')
    cover_letter = models.FileField(upload_to='cover_letters/', blank=True, null=True)
    
    # Details
    current_position = models.CharField(max_length=200, blank=True)
    current_employer = models.CharField(max_length=200, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    education = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    
    # Social profiles
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    
    # Availability
    notice_period_days = models.PositiveIntegerField(default=30)
    available_from = models.DateField(null=True, blank=True)
    
    # Salary expectations
    expected_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Source
    source = models.CharField(
        max_length=50,
        choices=[
            ('WEBSITE', 'Company Website'),
            ('REFERRAL', 'Employee Referral'),
            ('JOB_BOARD', 'Job Board'),
            ('LINKEDIN', 'LinkedIn'),
            ('RECRUITMENT_AGENCY', 'Recruitment Agency'),
            ('SOCIAL_MEDIA', 'Social Media'),
            ('OTHER', 'Other'),
        ],
        default='WEBSITE'
    )
    referrer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_candidates'
    )
    
    notes = models.TextField(blank=True)
    
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Application(models.Model):
    """
    Job applications
    """
    class ApplicationStage(models.TextChoices):
        APPLIED = 'APPLIED', 'Applied'
        SCREENING = 'SCREENING', 'Screening'
        SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
        INTERVIEW = 'INTERVIEW', 'Interview'
        ASSESSMENT = 'ASSESSMENT', 'Assessment'
        REFERENCE_CHECK = 'REFERENCE_CHECK', 'Reference Check'
        OFFER = 'OFFER', 'Offer'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
        HIRED = 'HIRED', 'Hired'

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(JobPosition, on_delete=models.CASCADE, related_name='applications')
    
    stage = models.CharField(max_length=20, choices=ApplicationStage.choices, default=ApplicationStage.APPLIED)
    
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Screening
    screening_score = models.PositiveIntegerField(null=True, blank=True)
    screening_notes = models.TextField(blank=True)
    screened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='screened_applications'
    )
    
    # Overall assessment
    overall_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Rejection
    rejection_reason = models.TextField(blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_applications'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('candidate', 'job')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.candidate} for {self.job.title}"


class Interview(models.Model):
    """
    Interview scheduling and feedback
    """
    class InterviewType(models.TextChoices):
        PHONE = 'PHONE', 'Phone Screening'
        VIDEO = 'VIDEO', 'Video Interview'
        IN_PERSON = 'IN_PERSON', 'In-Person'
        TECHNICAL = 'TECHNICAL', 'Technical Interview'
        PANEL = 'PANEL', 'Panel Interview'
        FINAL = 'FINAL', 'Final Interview'

    class InterviewStatus(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        COMPLETED = 'COMPLETED', 'Completed'
        NO_SHOW = 'NO_SHOW', 'No Show'
        CANCELLED = 'CANCELLED', 'Cancelled'
        RESCHEDULED = 'RESCHEDULED', 'Rescheduled'

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interviewers = models.ManyToManyField(Employee, related_name='interviews_conducted')
    
    interview_type = models.CharField(max_length=20, choices=InterviewType.choices)
    status = models.CharField(max_length=20, choices=InterviewStatus.choices, default=InterviewStatus.SCHEDULED)
    
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    location = models.CharField(max_length=200, blank=True)
    meeting_link = models.URLField(blank=True)
    
    # Feedback
    notes = models.TextField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    recommendation = models.CharField(
        max_length=20,
        choices=[
            ('STRONG_YES', 'Strong Yes'),
            ('YES', 'Yes'),
            ('MAYBE', 'Maybe'),
            ('NO', 'No'),
            ('STRONG_NO', 'Strong No'),
        ],
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.interview_type} for {self.application}"
