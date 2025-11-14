from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer
from .permissions import IsOwnerOrAssigneeOrAdmin
from apps.accounts.permissions import IsAdminOrReadOnly

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().select_related('assigned_to__user', 'created_by__user', 'project')
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAssigneeOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Task.objects.all()
        
        employee = user.employee_profile
        return Task.objects.filter(
            Q(assigned_to=employee) |
            Q(created_by=employee)
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)