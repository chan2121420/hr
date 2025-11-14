from django.contrib import admin
from .models import JobPosition, Candidate, Application, Interview

@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'hiring_manager', 'status', 'posted_at')
    list_filter = ('status', 'department')
    search_fields = ('title', 'department__name')

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone_number')
    search_fields = ('email', 'first_name', 'last_name')

class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 1

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'stage', 'applied_at')
    list_filter = ('stage', 'job')
    search_fields = ('candidate__email', 'job__title')
    inlines = [InterviewInline]