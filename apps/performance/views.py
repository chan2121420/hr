from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Goal, PerformanceReview
from .serializers import GoalSerializer, PerformanceReviewSerializer
from .permissions import IsOwnerOrManagerOrAdmin

class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all().select_related('employee__user')
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrAdmin]

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
        if self.request.user.is_staff:
            serializer.save()
        else:
            serializer.save(employee=self.request.user.employee_profile)

class PerformanceReviewViewSet(viewsets.ModelViewSet):
    queryset = PerformanceReview.objects.all().select_related(
        'employee__user', 
        'reviewer__user'
    ).prefetch_related('goals_discussed')
    serializer_class = PerformanceReviewSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return PerformanceReview.objects.all()
            
        employee = user.employee_profile
        return PerformanceReview.objects.filter(
            Q(employee=employee) | 
            Q(employee__manager=employee) |
            Q(reviewer=employee)
        )