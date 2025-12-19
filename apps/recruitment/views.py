from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from .models import JobPosition, Candidate, Application, Interview
from .serializers import (
    JobPositionSerializer, 
    CandidateSerializer, 
    ApplicationSerializer, 
    InterviewSerializer
)
from apps.accounts.permissions import IsAdminOrReadOnly

class JobPositionViewSet(viewsets.ModelViewSet):
    queryset = JobPosition.objects.all().prefetch_related('applications')
    serializer_class = JobPositionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        # Public users/Employees only see OPEN jobs
        if not self.request.user.is_staff:
            return JobPosition.objects.filter(status='OPEN')
        return JobPosition.objects.all()
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def applications(self, request, pk=None):
        job = self.get_object()
        applications = job.applications.all().select_related('candidate')
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [IsAdminUser]

class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    # AllowAny for creating applications (external candidates)
    # But restrict listing/viewing to Admins
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]

class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = [IsAdminUser]