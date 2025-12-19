from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer
from apps.accounts.permissions import IsAdminOrReadOnly
from rest_framework.exceptions import PermissionDenied

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().select_related('assigned_to__user', 'created_by__user', 'project')
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Task.objects.all()
        # Users see tasks assigned to them OR created by them
        employee = user.employee_profile
        return Task.objects.filter(
            Q(assigned_to=employee) | 
            Q(created_by=employee)
        )

    def perform_create(self, serializer):
        # Automatically set the creator to the current user
        serializer.save(created_by=self.request.user.employee_profile)

    def perform_update(self, serializer):
        # Only allow assignees or creators (or admin) to update
        instance = self.get_object()
        user_emp = self.request.user.employee_profile
        if not (self.request.user.is_staff or instance.created_by == user_emp or instance.assigned_to == user_emp):
             raise PermissionDenied("You do not have permission to edit this task.")
        serializer.save()