from rest_framework import serializers
from .models import (
    Task, TaskCategory, TaskComment, TaskAttachment, 
    TaskAllocationRule, EmployeeTaskPerformance, TaskTemplate
)

class TaskCategorySerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskCategory
        fields = '__all__'
    
    def get_task_count(self, obj):
        return obj.tasks.filter(status__in=['assigned', 'in_progress']).count()

class TaskCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = TaskComment
        fields = '__all__'

class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = '__all__'

class TaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for task list"""
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'category', 'category_name',
            'assigned_to', 'assigned_to_name', 'assigned_by',
            'assigned_by_name', 'priority', 'status', 'due_date',
            'completion_percentage', 'is_overdue', 'days_until_due'
        ]

class TaskDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single task view"""
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    completed_by_name = serializers.CharField(source='completed_by.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    
    is_overdue = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    
    class Meta:
        model = Task
        fields = '__all__'

class EmployeeTaskPerformanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    
    class Meta:
        model = EmployeeTaskPerformance
        fields = '__all__'

class TaskAllocationRuleSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = TaskAllocationRule
        fields = '__all__'

class TaskTemplateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = TaskTemplate
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'