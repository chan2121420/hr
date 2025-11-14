from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Q
from .models import LeaveType, Holiday, LeaveRequest
from .serializers import (
    LeaveTypeSerializer, 
    HolidaySerializer, 
    LeaveRequestSerializer,
    LeaveApprovalSerializer
)
from .permissions import IsOwnerOrManagerOrAdmin, IsManagerOrAdmin

class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAdminUser]

class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAdminUser]

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all().select_related('employee__user', 'leave_type', 'reviewed_by')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return LeaveRequest.objects.all()
        
        employee = user.employee_profile
        return LeaveRequest.objects.filter(
            Q(employee=employee) | 
            Q(employee__manager=employee)
        )

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user.employee_profile)

    @action(detail=True, methods=['post'], 
            permission_classes=[IsManagerOrAdmin], 
            serializer_class=LeaveApprovalSerializer)
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        if leave_request.status != 'PENDING':
            return Response(
                {"error": "This request is not pending approval."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        leave_request.status = LeaveRequest.LeaveStatus.APPROVED
        leave_request.reviewed_by = request.user.employee_profile
        leave_request.review_comments = serializer.validated_data.get('review_comments', 'Approved')
        leave_request.save()
        
        return Response(LeaveRequestSerializer(leave_request).data)

    @action(detail=True, methods=['post'], 
            permission_classes=[IsManagerOrAdmin],
            serializer_class=LeaveApprovalSerializer)
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        if leave_request.status != 'PENDING':
            return Response(
                {"error": "This request is not pending approval."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        leave_request.status = LeaveRequest.LeaveStatus.REJECTED
        leave_request.reviewed_by = request.user.employee_profile
        leave_request.review_comments = serializer.validated_data.get('review_comments', 'Rejected')
        leave_request.save()
        
        return Response(LeaveRequestSerializer(leave_request).data)