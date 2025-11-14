from django.contrib import admin
from .models import TrainingCourse, CourseSession, Enrollment

@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider')
    search_fields = ('title', 'provider')

class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 1
    autocomplete_fields = ('employee',)

@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ('course', 'start_date', 'end_date', 'location', 'instructor')
    list_filter = ('course', 'start_date', 'location')
    inlines = [EnrollmentInline]
    search_fields = ('course__title', 'location', 'instructor') # <-- THIS LINE IS ADDED

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'session', 'status', 'score')
    list_filter = ('status', 'session__course')
    search_fields = ('employee__user__email', 'session__course__title')
    autocomplete_fields = ('employee', 'session')