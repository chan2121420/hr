from django.contrib import admin
from .models import Goal, PerformanceReview

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'due_date', 'status')
    list_filter = ('status', 'due_date')
    search_fields = ('title', 'employee__user__email')

@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ('employee', 'reviewer', 'review_date', 'status', 'overall_rating')
    list_filter = ('status', 'review_date', 'overall_rating')
    search_fields = ('employee__user__email', 'reviewer__user__email')
    filter_horizontal = ('goals_discussed',)