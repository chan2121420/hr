from rest_framework import serializers
from .models import Course, TrainingSession, TrainingEnrollment

class CourseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Course
        fields = '__all__'

class TrainingSessionSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    facilitator_name = serializers.CharField(source='facilitator.get_full_name', read_only=True)
    enrollment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingSession
        fields = '__all__'
    
    def get_enrollment_count(self, obj):
        return obj.enrollments.count()

class TrainingEnrollmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    
    class Meta:
        model = TrainingEnrollment
        fields = '__all__'