from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Employee, EmployeeSkill
from .serializers import EmployeeListSerializer, EmployeeDetailSerializer
from .filters import EmployeeFilter


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    Employee CRUD operations with filtering, search, and ordering.
    """
    queryset = Employee.objects.select_related(
        'department', 'position', 'manager', 'company'
    ).prefetch_related('skills', 'documents')

    # Default serializer
    serializer_class = EmployeeListSerializer
    permission_classes = [IsAuthenticated]

    # Filters, search, ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EmployeeFilter
    search_fields = ['first_name', 'last_name', 'employee_id', 'work_email']
    ordering_fields = ['employee_id', 'date_joined', 'first_name']
    ordering = ['employee_id']  # default ordering

    def get_serializer_class(self):
        """Return detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return EmployeeDetailSerializer
        return EmployeeListSerializer

    @action(detail=True, methods=['get'])
    def performance_summary(self, request, pk=None):
        """Get employee performance summary"""
        employee = self.get_object()

        # Fallback if employee has no performance objects
        task_perf = getattr(employee, 'task_performance', None)
        reviews = getattr(employee, 'performance_reviews', Employee.objects.none()).filter(
            status='completed'
        ).order_by('-created_at')[:5]
        goals = getattr(employee, 'goals', Employee.objects.none()).filter(
            status__in=['in_progress', 'approved']
        )

        return Response({
            'task_performance': {
                'overall_score': getattr(task_perf, 'overall_performance_score', 0),
                'completion_rate': (
                    task_perf.tasks_completed_on_time / task_perf.total_tasks_completed * 100
                    if task_perf and task_perf.total_tasks_completed > 0 else 0
                ),
                'current_workload': getattr(task_perf, 'current_task_count', 0)
            },
            'recent_reviews': [
                {
                    'cycle': getattr(r.cycle, 'name', ''),
                    'rating': getattr(r, 'overall_rating', 0),
                    'date': getattr(r, 'completed_at', None)
                } for r in reviews
            ],
            'active_goals': [
                {
                    'title': getattr(g, 'title', ''),
                    'progress': getattr(g, 'progress_percentage', 0),
                    'due_date': getattr(g, 'due_date', None)
                } for g in goals
            ]
        })

    @action(detail=True, methods=['post'])
    def add_skill(self, request, pk=None):
        """Add a skill to an employee"""
        employee = self.get_object()
        skill_data = request.data

        skill = EmployeeSkill.objects.create(
            employee=employee,
            skill_name=skill_data.get('skill_name'),
            proficiency=skill_data.get('proficiency'),
            years_experience=skill_data.get('years_experience', None),
            certified=skill_data.get('certified', False)
        )

        return Response({
            'message': 'Skill added successfully',
            'skill': {
                'name': skill.skill_name,
                'proficiency': skill.proficiency,
                'years_experience': skill.years_experience,
                'certified': skill.certified
            }
        }, status=status.HTTP_201_CREATED)
