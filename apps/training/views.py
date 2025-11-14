from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Q
from .models import TrainingCourse, CourseSession, Enrollment
from .serializers import (
    TrainingCourseSerializer, 
    CourseSessionSerializer, 
    EnrollmentSerializer,
    EnrollmentCreateSerializer
)
from apps.accounts.permissions import IsAdminOrReadOnly

class TrainingCourseViewSet(viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.all()
    serializer_class = TrainingCourseSerializer
    permission_classes = [IsAdminOrReadOnly]

class CourseSessionViewSet(viewsets.ModelViewSet):
    queryset = CourseSession.objects.all().select_related('course')
    serializer_class = CourseSessionSerializer
    permission_classes = [IsAdminOrReadOnly]

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all().select_related('employee__user', 'session__course')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return EnrollmentCreateSerializer
        return EnrollmentSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Enrollment.objects.all()
        return Enrollment.objects.filter(employee=user.employee_profile)
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]