from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import LeaveType, LeavePolicy, LeaveBalance, LeaveRequest
from .serializers import (
    LeaveTypeSerializer,
    LeavePolicySerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer
)

class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'days_allowed_per_year']

class LeavePolicyViewSet(viewsets.ModelViewSet):
    queryset = LeavePolicy.objects.select_related('leave_type')
    serializer_class = LeavePolicySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'leave_type__name']
    ordering_fields = ['name']

class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.select_related('employee', 'leave_type')
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'leave_type', 'year']
    search_fields = ['employee__first_name', 'employee__last_name', 'leave_type__name']
    ordering_fields = ['year', 'total_days']

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related('employee', 'leave_type', 'approved_by', 'rejected_by', 'handover_to')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'leave_type', 'status', 'start_date', 'end_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'leave_type__name']
    ordering_fields = ['start_date', 'end_date', 'status']

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a leave request for approval"""
        leave_request = self.get_object()
        if leave_request.status != 'draft':
            return Response({'error': 'Only draft leave requests can be submitted'}, status=status.HTTP_400_BAD_REQUEST)
        
        leave_request.status = 'submitted'
        leave_request.submitted_at = timezone.now()
        leave_request.save()
        return Response({'message': 'Leave request submitted successfully'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a leave request"""
        leave_request = self.get_object()
        if leave_request.status not in ['submitted', 'pending_approval']:
            return Response({'error': 'Only submitted or pending leave requests can be approved'}, status=status.HTTP_400_BAD_REQUEST)
        
        leave_request.status = 'approved'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.approval_comments = request.data.get('comments', '')
        leave_request.save()
        return Response({'message': 'Leave request approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave request"""
        leave_request = self.get_object()
        if leave_request.status not in ['submitted', 'pending_approval']:
            return Response({'error': 'Only submitted or pending leave requests can be rejected'}, status=status.HTTP_400_BAD_REQUEST)
        
        leave_request.status = 'rejected'
        leave_request.rejected_by = request.user
        leave_request.rejected_at = timezone.now()
        leave_request.rejection_reason = request.data.get('reason', '')
        leave_request.save()
        return Response({'message': 'Leave request rejected'})
