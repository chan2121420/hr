from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.utils import timezone
from .models import Shift, AttendanceRecord
from .serializers import (
    ShiftSerializer, 
    AttendanceRecordSerializer, 
    ClockInSerializer, 
    ClockOutSerializer
)
from .permissions import IsOwnerOrAdmin
from apps.employees.models import Employee

class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [IsAdminUser]

class AttendanceRecordViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.all().select_related('employee__user', 'shift')
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AttendanceRecord.objects.all()
        return AttendanceRecord.objects.filter(employee=user.employee_profile)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def clock_in(self, request):
        employee = request.user.employee_profile
        today = timezone.now().date()
        
        record, created = AttendanceRecord.objects.get_or_create(
            employee=employee,
            date=today
        )
        
        if record.clock_in:
            return Response(
                {"error": "You have already clocked in today."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record.clock_in = timezone.now()
        record.status = 'PRESENT'
        record.shift = employee.shift
        record.save()
        
        serializer = AttendanceRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def clock_out(self, request):
        employee = request.user.employee_profile
        today = timezone.now().date()
        
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
        except AttendanceRecord.DoesNotExist:
            return Response(
                {"error": "You have not clocked in today."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        if not record.clock_in:
             return Response(
                {"error": "You have not clocked in today."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if record.clock_out:
            return Response(
                {"error": "You have already clocked out today."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        record.clock_out = timezone.now()
        record.save()
        
        serializer = AttendanceRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def today(self, request):
        employee = request.user.employee_profile
        today = timezone.now().date()
        
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
            serializer = AttendanceRecordSerializer(record)
            return Response(serializer.data)
        except AttendanceRecord.DoesNotExist:
            return Response(
                {"status": "NOT_STARTED", "clock_in": None, "clock_out": None},
                status=status.HTTP_200_OK
            )