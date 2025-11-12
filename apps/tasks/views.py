from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from datetime import date
from .models import Task, EmployeeTaskPerformance
from .serializers import TaskSerializer, TaskDetailSerializer
from apps.core.utils import allocate_task_to_best_employee, send_notification

class TaskViewSet(viewsets.ModelViewSet):
    """
    Task management with intelligent allocation
    """
    queryset = Task.objects.select_related(
        'assigned_to', 'assigned_by', 'category', 'department'
    ).prefetch_related('comments', 'attachments')
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'employee':
            queryset = queryset.filter(assigned_to=user.employee)
        elif user.role in ['dept_manager', 'team_lead']:
            queryset = queryset.filter(
                Q(department=user.employee.department) |
                Q(assigned_to__manager=user.employee)
            )
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        task = serializer.save(assigned_by=self.request.user)
        
        # Auto-allocate if no assignee specified
        if not task.assigned_to and task.department:
            assigned_employee = allocate_task_to_best_employee(task)
            
            if assigned_employee:
                # Send notification
                send_notification(
                    user=assigned_employee.user_account,
                    notification_type='task',
                    title='New Task Assigned',
                    message=f'You have been assigned: {task.title}',
                    related_model='Task',
                    related_object_id=task.id,
                    send_email=True
                )
    
    @action(detail=True, methods=['post'])
    def start_task(self, request, pk=None):
        """Start working on a task"""
        task = self.get_object()
        
        if task.status != 'assigned':
            return Response(
                {'error': 'Task must be in assigned status to start'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = 'in_progress'
        task.start_date = timezone.now().date()
        task.save()
        
        return Response({'message': 'Task started successfully'})
    
    @action(detail=True, methods=['post'])
    def complete_task(self, request, pk=None):
        """Complete a task"""
        task = self.get_object()
        
        task.status = 'completed'
        task.completion_percentage = 100
        task.completed_at = timezone.now()
        task.completed_by = request.user.employee
        task.actual_hours = request.data.get('actual_hours')
        task.save()
        
        # Calculate performance score
        performance_score = task.calculate_performance_score()
        
        # Update employee performance metrics
        if task.assigned_to:
            task_perf = EmployeeTaskPerformance.objects.get(
                employee=task.assigned_to
            )
            task_perf.calculate_metrics()
        
        return Response({
            'message': 'Task completed successfully',
            'performance_score': performance_score
        })
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get task analytics"""
        user = request.user
        
        if user.role == 'employee':
            tasks = Task.objects.filter(assigned_to=user.employee)
        elif user.role in ['dept_manager', 'team_lead']:
            tasks = Task.objects.filter(department=user.employee.department)
        else:
            tasks = Task.objects.all()
        
        analytics = {
            'total_tasks': tasks.count(),
            'by_status': tasks.values('status').annotate(count=Count('id')),
            'by_priority': tasks.values('priority').annotate(count=Count('id')),
            'overdue_tasks': tasks.filter(
                due_date__lt=date.today(),
                status__in=['assigned', 'in_progress']
            ).count(),
            'completion_rate': tasks.filter(
                status='completed',
                completed_at__date__lte=F('due_date')
            ).count() / max(tasks.filter(status='completed').count(), 1) * 100,
            'avg_completion_time': tasks.filter(
                status='completed',
                actual_hours__isnull=False
            ).aggregate(avg=Avg('actual_hours'))['avg']
        }
        
        return Response(analytics)