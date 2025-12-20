from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from datetime import date, timedelta, datetime
from decimal import Decimal

from .models import (
    Shift, AttendanceRecord, AttendanceBreak, AttendanceException,
    AttendancePolicy, AttendanceSummary, PublicHoliday
)
from .serializers import (
    ShiftSerializer, ShiftDetailSerializer,
    AttendanceRecordSerializer, AttendanceRecordDetailSerializer,
    AttendanceBreakSerializer, AttendanceExceptionSerializer,
    AttendancePolicySerializer, AttendanceSummarySerializer,
    PublicHolidaySerializer, ClockInSerializer, ClockOutSerializer
)
from .permissions import IsOwnerOrAdmin, CanManageAttendance
from .filters import AttendanceRecordFilter, AttendanceExceptionFilter


class ShiftViewSet(viewsets.ModelViewSet):
    """Enhanced shift management"""
    queryset = Shift.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['start_time', 'name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ShiftDetailSerializer
        return ShiftSerializer

    def get_queryset(self):
        queryset = Shift.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """Get employees assigned to this shift"""
        shift = self.get_object()
        from apps.employees.models import Employee
        employees = Employee.objects.filter(shift=shift, status='ACTIVE')
        
        from apps.employees.serializers import EmployeeSerializer
        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Get schedule for this shift"""
        shift = self.get_object()
        start_date = request.query_params.get('start_date', date.today())
        end_date = request.query_params.get('end_date', date.today() + timedelta(days=7))
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        records = AttendanceRecord.objects.filter(
            shift=shift,
            date__range=[start_date, end_date]
        )
        
        serializer = AttendanceRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get shift summary statistics"""
        shifts = self.get_queryset().filter(is_active=True)
        
        data = []
        for shift in shifts:
            employee_count = shift.employees.filter(status='ACTIVE').count()
            data.append({
                'id': str(shift.id),
                'name': shift.name,
                'expected_hours': shift.expected_hours,
                'employee_count': employee_count,
                'working_days': shift.working_days_count,
            })
        
        return Response(data)


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    """Enhanced attendance record management"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AttendanceRecordFilter
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    ordering_fields = ['date', 'clock_in', 'work_hours']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AttendanceRecordDetailSerializer
        elif self.action == 'clock_in':
            return ClockInSerializer
        elif self.action == 'clock_out':
            return ClockOutSerializer
        return AttendanceRecordSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = AttendanceRecord.objects.select_related(
            'employee__user', 'shift', 'approved_by'
        ).prefetch_related('breaks', 'exceptions')
        
        if user.is_staff:
            return queryset
        
        # Regular employees see their own records
        try:
            return queryset.filter(employee=user.employee_profile)
        except:
            return queryset.none()

    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """Clock in for the day"""
        try:
            employee = request.user.employee_profile
        except:
            return Response(
                {'error': 'Employee profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        today = timezone.now().date()
        
        # Check if already clocked in
        record, created = AttendanceRecord.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={'shift': employee.shift}
        )
        
        if record.clock_in:
            return Response(
                {'error': 'Already clocked in today', 'record': AttendanceRecordSerializer(record).data},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Capture clock in details
        record.clock_in = timezone.now()
        record.status = AttendanceRecord.AttendanceStatus.PRESENT
        record.shift = employee.shift
        record.clock_in_ip = self.get_client_ip(request)
        record.clock_in_device = request.META.get('HTTP_USER_AGENT', '')[:200]
        record.clock_in_user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Location tracking
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        if latitude and longitude:
            record.clock_in_latitude = Decimal(str(latitude))
            record.clock_in_longitude = Decimal(str(longitude))
            record.clock_in_location = request.data.get('location', '')
        
        # Photo verification
        if 'photo' in request.FILES:
            record.clock_in_photo = request.FILES['photo']
        
        # Check if remote
        record.is_remote = request.data.get('is_remote', False)
        
        record.save()
        
        return Response(
            {
                'message': 'Clocked in successfully',
                'record': AttendanceRecordSerializer(record).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def clock_out(self, request):
        """Clock out for the day"""
        try:
            employee = request.user.employee_profile
        except:
            return Response(
                {'error': 'Employee profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        today = timezone.now().date()
        
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
        except AttendanceRecord.DoesNotExist:
            return Response(
                {'error': 'No clock in record found for today'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not record.clock_in:
            return Response(
                {'error': 'Please clock in first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if record.clock_out:
            return Response(
                {'error': 'Already clocked out today', 'record': AttendanceRecordSerializer(record).data},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Capture clock out details
        record.clock_out = timezone.now()
        record.clock_out_ip = self.get_client_ip(request)
        record.clock_out_device = request.META.get('HTTP_USER_AGENT', '')[:200]
        record.clock_out_user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Location tracking
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        if latitude and longitude:
            record.clock_out_latitude = Decimal(str(latitude))
            record.clock_out_longitude = Decimal(str(longitude))
            record.clock_out_location = request.data.get('location', '')
        
        # Photo verification
        if 'photo' in request.FILES:
            record.clock_out_photo = request.FILES['photo']
        
        # Work summary
        record.work_summary = request.data.get('work_summary', '')
        record.tasks_completed = request.data.get('tasks_completed', 0)
        record.productive_hours = request.data.get('productive_hours', 0)
        
        record.save()
        
        return Response({
            'message': 'Clocked out successfully',
            'record': AttendanceRecordDetailSerializer(record).data,
            'work_hours': record.work_hours,
            'overtime_hours': record.overtime_hours
        })

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's attendance record"""
        try:
            employee = request.user.employee_profile
        except:
            return Response(
                {'error': 'Employee profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        today = timezone.now().date()
        
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
            return Response(AttendanceRecordDetailSerializer(record).data)
        except AttendanceRecord.DoesNotExist:
            return Response({
                'status': 'NOT_STARTED',
                'date': today,
                'message': 'No attendance record for today'
            })

    @action(detail=False, methods=['get'])
    def my_attendance(self, request):
        """Get current user's attendance records"""
        try:
            employee = request.user.employee_profile
        except:
            return Response(
                {'error': 'Employee profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = AttendanceRecord.objects.filter(employee=employee)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        queryset = queryset.order_by('-date')[:30]
        
        serializer = AttendanceRecordSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve attendance record"""
        record = self.get_object()
        
        try:
            approver = request.user.employee_profile
        except:
            return Response(
                {'error': 'Approver profile not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record.is_verified = True
        record.approved_by = approver
        record.approved_at = timezone.now()
        record.save()
        
        return Response({'message': 'Attendance record approved'})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get attendance statistics"""
        employee_id = request.query_params.get('employee_id')
        start_date = request.query_params.get('start_date', date.today() - timedelta(days=30))
        end_date = request.query_params.get('end_date', date.today())
        
        queryset = AttendanceRecord.objects.all()
        
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        elif not request.user.is_staff:
            try:
                queryset = queryset.filter(employee=request.user.employee_profile)
            except:
                return Response({'error': 'Employee profile not found'}, status=404)
        
        queryset = queryset.filter(date__range=[start_date, end_date])
        
        stats = {
            'total_days': queryset.count(),
            'present_days': queryset.filter(
                Q(status='PRESENT') | Q(status='LATE') | Q(status='OVERTIME')
            ).count(),
            'absent_days': queryset.filter(status__in=['ABSENT', 'UNAUTHORIZED']).count(),
            'late_days': queryset.filter(is_late=True).count(),
            'leave_days': queryset.filter(status__in=['ON_LEAVE', 'SICK_LEAVE']).count(),
            'total_hours': sum(r.work_hours for r in queryset),
            'total_overtime': sum(r.overtime_hours for r in queryset),
            'average_hours': queryset.aggregate(Avg('work_hours'))['work_hours__avg'] or 0,
            'attendance_rate': 0,
            'punctuality_rate': 0,
        }
        
        if stats['total_days'] > 0:
            stats['attendance_rate'] = round(
                (stats['present_days'] / stats['total_days']) * 100, 2
            )
        
        if stats['present_days'] > 0:
            on_time = stats['present_days'] - stats['late_days']
            stats['punctuality_rate'] = round((on_time / stats['present_days']) * 100, 2)
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def team_attendance(self, request):
        """Get team attendance for managers"""
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        if not employee.is_manager and not request.user.is_staff:
            return Response(
                {'error': 'Only managers can view team attendance'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        today = timezone.now().date()
        
        # Get team members
        team_members = employee.subordinates.filter(status='ACTIVE')
        
        records = AttendanceRecord.objects.filter(
            employee__in=team_members,
            date=today
        )
        
        serializer = AttendanceRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def start_break(self, request):
        """Start a break"""
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        today = timezone.now().date()
        
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
        except AttendanceRecord.DoesNotExist:
            return Response(
                {'error': 'No attendance record found. Please clock in first.'},
                status=404
            )
        
        # Check if there's an ongoing break
        ongoing_break = record.breaks.filter(break_end__isnull=True).first()
        if ongoing_break:
            return Response(
                {'error': 'You already have an ongoing break'},
                status=400
            )
        
        break_obj = AttendanceBreak.objects.create(
            attendance_record=record,
            break_start=timezone.now(),
            break_type=request.data.get('break_type', 'LUNCH')
        )
        
        return Response(AttendanceBreakSerializer(break_obj).data, status=201)

    @action(detail=False, methods=['post'])
    def end_break(self, request):
        """End current break"""
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        today = timezone.now().date()
        
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
        except AttendanceRecord.DoesNotExist:
            return Response({'error': 'No attendance record found'}, status=404)
        
        ongoing_break = record.breaks.filter(break_end__isnull=True).first()
        if not ongoing_break:
            return Response({'error': 'No ongoing break found'}, status=404)
        
        ongoing_break.break_end = timezone.now()
        ongoing_break.save()
        
        return Response(AttendanceBreakSerializer(ongoing_break).data)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AttendanceExceptionViewSet(viewsets.ModelViewSet):
    """Manage attendance exceptions"""
    serializer_class = AttendanceExceptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = AttendanceExceptionFilter
    ordering_fields = ['created_at', 'exception_date', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AttendanceException.objects.all()
        
        try:
            employee = user.employee_profile
            return AttendanceException.objects.filter(employee=employee)
        except:
            return AttendanceException.objects.none()

    def perform_create(self, serializer):
        try:
            serializer.save(employee=self.request.user.employee_profile)
        except:
            raise ValidationError('Employee profile not found')

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve exception"""
        exception = self.get_object()
        
        try:
            reviewer = request.user.employee_profile
        except:
            return Response({'error': 'Reviewer profile not found'}, status=400)
        
        exception.approve(reviewer)
        return Response({'message': 'Exception approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject exception"""
        exception = self.get_object()
        
        try:
            reviewer = request.user.employee_profile
        except:
            return Response({'error': 'Reviewer profile not found'}, status=400)
        
        comments = request.data.get('comments', '')
        exception.reject(reviewer, comments)
        return Response({'message': 'Exception rejected'})

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending exceptions"""
        queryset = self.get_queryset().filter(status='PENDING')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AttendanceSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """View attendance summaries"""
    serializer_class = AttendanceSummarySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AttendanceSummary.objects.all()
        
        try:
            return AttendanceSummary.objects.filter(employee=user.employee_profile)
        except:
            return AttendanceSummary.objects.none()

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def generate(self, request):
        """Generate summaries for all employees"""
        month = int(request.data.get('month', date.today().month))
        year = int(request.data.get('year', date.today().year))
        
        from apps.employees.models import Employee
        employees = Employee.objects.filter(status='ACTIVE')
        
        count = 0
        for employee in employees:
            summary, created = AttendanceSummary.objects.get_or_create(
                employee=employee,
                month=month,
                year=year
            )
            summary.regenerate()
            count += 1
        
        return Response({
            'message': f'Generated {count} summaries',
            'month': month,
            'year': year
        })


class PublicHolidayViewSet(viewsets.ModelViewSet):
    """Manage public holidays"""
    queryset = PublicHoliday.objects.all()
    serializer_class = PublicHolidaySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming holidays"""
        today = date.today()
        holidays = PublicHoliday.objects.filter(date__gte=today).order_by('date')[:10]
        serializer = self.get_serializer(holidays, many=True)
        return Response(serializer.data)