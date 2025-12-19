from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Goal, PerformanceReview
from .serializers import GoalSerializer, PerformanceReviewSerializer
from rest_framework.permissions import IsAuthenticated

class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all().select_related('employee__user')
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Goal.objects.all()
        
        employee = user.employee_profile
        return Goal.objects.filter(
            Q(employee=employee) | 
            Q(employee__manager=employee)
        )

    def perform_create(self, serializer):
        # If user is staff, they can set employee field, otherwise defaults to self
        if self.request.user.is_staff and 'employee' in serializer.validated_data:
            serializer.save(set_by=self.request.user.employee_profile)
        else:
            serializer.save(
                employee=self.request.user.employee_profile,
                set_by=self.request.user.employee_profile
            )

class PerformanceReviewViewSet(viewsets.ModelViewSet):
    queryset = PerformanceReview.objects.all()
    serializer_class = PerformanceReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return PerformanceReview.objects.all()
        employee = user.employee_profile
        return PerformanceReview.objects.filter(
            Q(employee=employee) | 
            Q(reviewer=employee)
        )