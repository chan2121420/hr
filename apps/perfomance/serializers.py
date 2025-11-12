from rest_framework import serializers
from .models import (
    PerformanceMetric, PerformanceCycle, EmployeeGoal,
    PerformanceReview, MetricRating, PerformanceImprovement
)

class PerformanceMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceMetric
        fields = '__all__'

class PerformanceCycleSerializer(serializers.ModelSerializer):
    active_reviews_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PerformanceCycle
        fields = '__all__'
    
    def get_active_reviews_count(self, obj):
        return obj.reviews.exclude(status='completed').count()

class EmployeeGoalSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)
    metric_name = serializers.CharField(source='metric.name', read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = EmployeeGoal
        fields = '__all__'

class MetricRatingSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='metric.name', read_only=True)
    metric_weight = serializers.DecimalField(source='metric.weight', max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = MetricRating
        fields = ['id', 'review', 'metric', 'metric_name', 'metric_weight', 'rating', 'comments', 'evidence']

class PerformanceReviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    metric_ratings = MetricRatingSerializer(many=True, read_only=True)
    
    class Meta:
        model = PerformanceReview
        fields = '__all__'

class PerformanceImprovementSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    
    class Meta:
        model = PerformanceImprovement
        fields = '__all__'