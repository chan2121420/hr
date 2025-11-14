from django.contrib import admin
from .models import Project, Task

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'status', 'priority', 'due_date', 'created_by')
    list_filter = ('status', 'priority', 'due_date', 'project')
    search_fields = ('title', 'assigned_to__user__email', 'created_by__user__email')
    autocomplete_fields = ('assigned_to', 'created_by', 'project')