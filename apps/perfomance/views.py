# apps/performance/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PerformanceReview, EmployeeGoal, PerformanceCycle
from .serializers import PerformanceReviewSerializer, EmployeeGoalSerializer

class PerformanceReviewViewSet(viewsets.ModelViewSet):
    """
    Performance review management
    """
    queryset = PerformanceReview.objects.select_related(
        'employee', 'cycle', 'reviewer'
    ).prefetch_related('metric_ratings')
    serializer_class = PerformanceReviewSerializer
    
    @action(detail=True, methods=['post'])
    def submit_review(self, request, pk=None):
        """Submit review for approval"""
        review = self.get_object()
        
        # Calculate overall rating
        overall_rating = review.calculate_overall_rating()
        review.overall_rating = overall_rating
        review.status = 'submitted'
        review.submitted_at = timezone.now()
        review.save()
        
        # Notify employee
        send_notification(
            user=review.employee.user_account,
            notification_type='approval',
            title='Performance Review Submitted',
            message=f'Your performance review for {review.cycle.name} has been submitted',
            send_email=True
        )
        
        return Response({'message': 'Review submitted successfully'})
    
    @action(detail=True, methods=['post'])
    def employee_acknowledge(self, request, pk=None):
        """Employee acknowledges review"""
        review = self.get_object()
        
        review.employee_comments = request.data.get('comments', '')
        review.employee_acknowledged = True
        review.acknowledged_at = timezone.now()
        review.status = 'acknowledged'
        review.save()
        
        return Response({'message': 'Review acknowledged'})

class EmployeeGoalViewSet(viewsets.ModelViewSet):
    """
    Employee goal management
    """
    queryset = EmployeeGoal.objects.select_related('employee', 'cycle', 'metric')
    serializer_class = EmployeeGoalSerializer
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update goal progress"""
        goal = self.get_object()
        
        goal.current_value = request.data.get('current_value', goal.current_value)
        goal.completion_percentage = request.data.get('completion_percentage', goal.completion_percentage)
        
        if goal.completion_percentage >= 100:
            goal.status = 'completed'
        
        goal.save()
        
        return Response({
            'message': 'Progress updated',
            'progress': goal.progress_percentage
        })