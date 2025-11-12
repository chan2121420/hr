from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Attendance, WorkSchedule, EmployeeSchedule, AttendanceException, Holiday
from .serializers import (
    AttendanceSerializer,
    WorkScheduleSerializer,
    AttendanceClockSerializer,
    AttendanceExceptionSerializer,
    HolidaySerializer
)

class WorkScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkSchedule.objects.all()
    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

class EmployeeScheduleViewSet(viewsets.ModelViewSet):
    queryset = EmployeeSchedule.objects.select_related('employee', 'schedule')
    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAuthenticated]

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('employee', 'approved_by')
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'date', 'status']
    search_fields = ['employee__first_name', 'employee__last_name']
    ordering_fields = ['date']

    @action(detail=True, methods=['post'])
    def clock_in(self, request, pk=None):
        attendance = self.get_object()
        data = request.data
        attendance.clock_in = data.get('clock_in')
        attendance.clock_in_location = data.get('location', '')
        attendance.save()
        return Response({'message': 'Clock-in recorded successfully'})

    @action(detail=True, methods=['post'])
    def clock_out(self, request, pk=None):
        attendance = self.get_object()
        data = request.data
        attendance.clock_out = data.get('clock_out')
        attendance.clock_out_location = data.get('location', '')
        attendance.calculate_hours()
        return Response({'message': 'Clock-out recorded successfully', 'hours_worked': attendance.hours_worked})

class AttendanceExceptionViewSet(viewsets.ModelViewSet):
    queryset = AttendanceException.objects.select_related('employee', 'attendance', 'reviewed_by')
    serializer_class = AttendanceExceptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'employee']
    search_fields = ['employee__first_name', 'employee__last_name']
    ordering_fields = ['created_at']

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        exception = self.get_object()
        exception.status = 'approved'
        exception.reviewed_by = request.user
        exception.reviewed_at = timezone.now()
        exception.review_comments = request.data.get('comments', '')
        exception.save()
        return Response({'message': 'Attendance exception approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        exception = self.get_object()
        exception.status = 'rejected'
        exception.reviewed_by = request.user
        exception.reviewed_at = timezone.now()
        exception.review_comments = request.data.get('comments', '')
        exception.save()
        return Response({'message': 'Attendance exception rejected'})

class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['date']
