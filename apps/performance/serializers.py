from rest_framework import serializers
from .models import Goal, PerformanceReview

class GoalSerializer(serializers.ModelSerializer):
    employee = serializers.StringRelatedField()
    
    class Meta:
        model = Goal
        fields = [
            'id', 
            'employee', 
            'title', 
            'description', 
            'due_date', 
            'status',
            'updated_at'
        ]

class PerformanceReviewSerializer(serializers.ModelSerializer):
    employee = serializers.StringRelatedField()
    reviewer = serializers.StringRelatedField()
    goals_discussed = GoalSerializer(many=True, read_only=True)
    
    class Meta:
        model = PerformanceReview
        fields = [
            'id', 
            'employee', 
            'reviewer', 
            'review_date', 
            'status', 
            'overall_rating', 
            'manager_comments',
            'employee_comments',
            'goals_discussed',
            'updated_at'
        ]