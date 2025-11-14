from rest_framework import serializers
from .models import TrainingCourse, CourseSession, Enrollment
from apps.employees.models import Employee

class TrainingCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCourse
        fields = ['id', 'title', 'description', 'provider']

class CourseSessionSerializer(serializers.ModelSerializer):
    course = serializers.StringRelatedField()
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=TrainingCourse.objects.all(),
        source='course',
        write_only=True
    )
    
    class Meta:
        model = CourseSession
        fields = ['id', 'course', 'course_id', 'start_date', 'end_date', 'location', 'instructor']

class EnrollmentSerializer(serializers.ModelSerializer):
    employee = serializers.StringRelatedField()
    session = CourseSessionSerializer()
    
    class Meta:
        model = Enrollment
        fields = ['id', 'employee', 'session', 'status', 'score', 'notes', 'enrolled_at']

class EnrollmentCreateSerializer(serializers.ModelSerializer):
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source='employee'
    )
    session_id = serializers.PrimaryKeyRelatedField(
        queryset=CourseSession.objects.all(),
        source='session'
    )
    
    class Meta:
        model = Enrollment
        fields = ['employee_id', 'session_id', 'status']