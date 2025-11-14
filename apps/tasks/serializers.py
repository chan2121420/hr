from rest_framework import serializers
from .models import Project, Task
from apps.employees.models import Employee

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description']

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source='assigned_to',
        write_only=True
    )
    
    class Meta:
        model = Task
        fields = [
            'id',
            'project',
            'title',
            'description',
            'status',
            'priority',
            'assigned_to',
            'assigned_to_id',
            'created_by',
            'due_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_by']