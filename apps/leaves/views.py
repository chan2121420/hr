from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg, F
from django.db.models.functions import TruncMonth, ExtractWeek
from django.utils import timezone
from django.core.exceptions import ValidationError  
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    LeaveType, Holiday, LeaveBalance, LeaveRequest, LeaveEncashment
)
from .serializers import (
    LeaveTypeSerializer, LeaveTypeDetailSerializer,
    HolidaySerializer, LeaveBalanceSerializer,
    LeaveRequestSerializer, LeaveRequestDetailSerializer,
    LeaveEncashmentSerializer, LeaveApprovalSerializer
)
from .permissions import IsOwnerOrManagerOrAdmin, IsManagerOrAdmin, CanApproveLeave  # Keep this
from .filters import LeaveRequestFilter, LeaveBalanceFilter

class LeaveTypeViewSet(viewsets.ModelViewSet):
    """Enhanced leave type management"""
    queryset = LeaveType.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'default_days_allocated']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LeaveTypeDetailSerializer
        return LeaveTypeSerializer

    def get_queryset(self):
        queryset = LeaveType.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=['get'])
    def eligibility(self, request, pk=None):
        """Check eligibility for this leave type"""
        leave_type = self.get_object()
        
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        is_eligible, message = leave_type.is_eligible(employee)
        
        # Get balance if eligible
        balance_info = None
        if is_eligible:
            try:
                balance = LeaveBalance.objects.get(
                    employee=employee,
                    leave_type=leave_type,
                    year=date.today().year
                )
                balance_info = {
                    'available': balance.available,
                    'total_allocated': float(balance.total_allocated),
                    'used': float(balance.used),
                    'pending': float(balance.pending)
                }
            except LeaveBalance.DoesNotExist:
                balance_info = {
                    'available': leave_type.default_days_allocated,
                    'total_allocated': leave_type.default_days_allocated,
                    'used': 0,
                    'pending': 0
                }
        
        return Response({
            'is_eligible': is_eligible,
            'message': message,
            'balance': balance_info
        })


class HolidayViewSet(viewsets.ModelViewSet):
    """Manage public holidays"""
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming holidays"""
        today = date.today()
        upcoming = Holiday.objects.filter(
            date__gte=today,
            date__lte=today + timedelta(days=90)
        ).order_by('date')
        
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Get holiday calendar for a year"""
        year = int(request.query_params.get('year', date.today().year))
        
        holidays = Holiday.objects.filter(
            date__year=year
        ).order_by('date')
        
        serializer = self.get_serializer(holidays, many=True)
        return Response(serializer.data)

@action(detail=False, methods=['get'])
def calendar_view(self, request):
    """Get calendar view with all leaves"""
    start_date = request.query_params.get('start')
    end_date = request.query_params.get('end')
    view_type = request.query_params.get('view', 'month')  # month, week, year
    
    # Get employee context
    employee = request.user.employee_profile
    
    # Base queryset
    queryset = LeaveRequest.objects.filter(
        status='APPROVED',
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    
    # Filter based on permissions
    if not request.user.is_staff:
        queryset = queryset.filter(
            Q(employee=employee) |
            Q(employee__department=employee.department) |
            Q(employee__manager=employee)
        )
    
    # Group by employee for better visualization
    calendar_data = []
    for leave in queryset.select_related('employee', 'leave_type'):
        calendar_data.append({
            'id': str(leave.id),
            'title': f"{leave.employee.full_name} - {leave.leave_type.name}",
            'start': leave.start_date,
            'end': leave.end_date,
            'color': leave.leave_type.color_code,
            'employee': leave.employee.full_name,
            'type': leave.leave_type.name,
            'isHalfDay': leave.is_half_day
        })
    
    return Response(calendar_data)
class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """View and manage leave balances"""
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LeaveBalanceFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return LeaveBalance.objects.all()
        
        try:
            return LeaveBalance.objects.filter(employee=user.employee_profile)
        except:
            return LeaveBalance.objects.none()

    @action(detail=False, methods=['get'])
    def my_balances(self, request):
        """Get current user's leave balances"""
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        year = int(request.query_params.get('year', date.today().year))
        
        balances = LeaveBalance.objects.filter(
            employee=employee,
            year=year
        )
        
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def adjust(self, request, pk=None):
        """Manually adjust leave balance"""
        balance = self.get_object()
        
        adjustment = Decimal(str(request.data.get('adjustment', 0)))
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Reason is required for balance adjustment'},
                status=400
            )
        
        balance.adjust_balance(adjustment, reason, request.user)
        
        return Response({
            'message': 'Balance adjusted successfully',
            'new_balance': balance.available
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def initialize_year(self, request):
        """Initialize leave balances for all employees for a year"""
        year = int(request.data.get('year', date.today().year))
        
        from apps.employees.models import Employee
        employees = Employee.objects.filter(status='ACTIVE')
        leave_types = LeaveType.objects.filter(is_active=True)
        
        created_count = 0
        for employee in employees:
            for leave_type in leave_types:
                balance, created = LeaveBalance.objects.get_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=year,
                    defaults={
                        'total_allocated': leave_type.default_days_allocated
                    }
                )
                if created:
                    created_count += 1
        
        return Response({
            'message': f'Initialized {created_count} leave balances for year {year}'
        })


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """Enhanced leave request management"""
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LeaveRequestFilter
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'reason']
    ordering_fields = ['requested_at', 'start_date', 'status']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LeaveRequestDetailSerializer
        elif self.action in ['approve', 'reject']:
            return LeaveApprovalSerializer
        return LeaveRequestSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveRequest.objects.select_related(
            'employee__user', 'leave_type', 'manager_approved_by',
            'covering_employee'
        )
        
        if user.is_staff:
            return queryset
        
        try:
            employee = user.employee_profile
            return queryset.filter(
                Q(employee=employee) |
                Q(employee__manager=employee) |
                Q(covering_employee=employee)
            )
        except:
            return queryset.none()

    def perform_create(self, serializer):
        try:
            employee = self.request.user.employee_profile
        except:
            raise ValidationError('Employee profile not found')
        
        serializer.save(employee=employee)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get current user's leave requests"""
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        queryset = LeaveRequest.objects.filter(employee=employee).order_by('-requested_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get leave requests pending approval"""
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        if not employee.is_manager and not request.user.is_staff:
            return Response(
                {'error': 'Only managers can view pending approvals'},
                status=403
            )
        
        queryset = LeaveRequest.objects.filter(
            employee__manager=employee,
            status='PENDING'
        ).order_by('requested_at')
        
        serializer = LeaveRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def approve(self, request, pk=None):
        """Approve leave request"""
        leave_request = self.get_object()
        
        if leave_request.status not in ['PENDING', 'MANAGER_APPROVED']:
            return Response(
                {'error': 'This request cannot be approved'},
                status=400
            )
        
        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comments = serializer.validated_data.get('review_comments', '')
        
        try:
            approver = request.user.employee_profile
            
            # Manager approval
            if leave_request.status == 'PENDING':
                leave_request.approve_by_manager(approver, comments)
            # HR approval
            elif leave_request.status == 'MANAGER_APPROVED':
                leave_request.approve_by_hr(request.user, comments)
            
            return Response({
                'message': 'Leave request approved',
                'request': LeaveRequestDetailSerializer(leave_request).data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrAdmin])
    def reject(self, request, pk=None):
        """Reject leave request"""
        leave_request = self.get_object()
        
        if leave_request.status not in ['PENDING', 'MANAGER_APPROVED']:
            return Response(
                {'error': 'This request cannot be rejected'},
                status=400
            )
        
        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data.get('review_comments', '')
        if not reason:
            return Response(
                {'error': 'Reason is required for rejection'},
                status=400
            )
        
        leave_request.reject(request.user, reason)
        
        return Response({
            'message': 'Leave request rejected',
            'request': LeaveRequestDetailSerializer(leave_request).data
        })

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw leave request"""
        leave_request = self.get_object()
        
        # Only owner can withdraw
        try:
            employee = request.user.employee_profile
            if leave_request.employee != employee:
                return Response(
                    {'error': 'You can only withdraw your own requests'},
                    status=403
                )
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        try:
            leave_request.withdraw()
            return Response({
                'message': 'Leave request withdrawn',
                'request': LeaveRequestDetailSerializer(leave_request).data
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def cancel(self, request, pk=None):
        """Cancel approved leave request"""
        leave_request = self.get_object()
        
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Cancellation reason is required'},
                status=400
            )
        
        try:
            leave_request.cancel(request.user, reason)
            return Response({
                'message': 'Leave request cancelled',
                'request': LeaveRequestDetailSerializer(leave_request).data
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Get leave calendar"""
        start_date = request.query_params.get('start_date', date.today())
        end_date = request.query_params.get('end_date', date.today() + timedelta(days=30))
        
        if isinstance(start_date, str):
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        queryset = LeaveRequest.objects.filter(
            status='APPROVED',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('employee__user', 'leave_type')
        
        # Filter by department if specified
        department_id = request.query_params.get('department')
        if department_id:
            queryset = queryset.filter(employee__department_id=department_id)
        
        serializer = LeaveRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get leave statistics"""
        employee_id = request.query_params.get('employee_id')
        start_date = request.query_params.get('start_date', date.today() - timedelta(days=365))
        end_date = request.query_params.get('end_date', date.today())
        
        queryset = LeaveRequest.objects.all()
        
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        elif not request.user.is_staff:
            try:
                queryset = queryset.filter(employee=request.user.employee_profile)
            except:
                return Response({'error': 'Employee profile not found'}, status=404)
        
        queryset = queryset.filter(
            start_date__gte=start_date,
            start_date__lte=end_date
        )
        
        stats = {
            'total_requests': queryset.count(),
            'approved': queryset.filter(status='APPROVED').count(),
            'pending': queryset.filter(status='PENDING').count(),
            'rejected': queryset.filter(status='REJECTED').count(),
            'by_leave_type': list(
                queryset.values('leave_type__name').annotate(count=Count('id'))
            ),
            'total_days_taken': sum(
                r.total_leave_days for r in queryset.filter(status='APPROVED')
            ),
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def team_calendar(self, request):
        """Get team leave calendar for managers"""
        try:
            employee = request.user.employee_profile
        except:
            return Response({'error': 'Employee profile not found'}, status=404)
        
        if not employee.is_manager and not request.user.is_staff:
            return Response(
                {'error': 'Only managers can view team calendar'},
                status=403
            )
        
        # Get team members
        team_members = employee.subordinates.filter(status='ACTIVE')
        
        # Get their leave requests
        month = int(request.query_params.get('month', date.today().month))
        year = int(request.query_params.get('year', date.today().year))
        
        queryset = LeaveRequest.objects.filter(
            employee__in=team_members,
            status='APPROVED',
            start_date__year=year,
            start_date__month=month
        )
        
        serializer = LeaveRequestSerializer(queryset, many=True)
        return Response(serializer.data)


class LeaveEncashmentViewSet(viewsets.ModelViewSet):
    """Manage leave encashment requests"""
    serializer_class = LeaveEncashmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return LeaveEncashment.objects.all()
        
        try:
            return LeaveEncashment.objects.filter(employee=user.employee_profile)
        except:
            return LeaveEncashment.objects.none()

    def perform_create(self, serializer):
        try:
            employee = self.request.user.employee_profile
        except:
            raise ValidationError('Employee profile not found')
        
        serializer.save(employee=employee)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve encashment request"""
        encashment = self.get_object()
        
        if encashment.status != 'PENDING':
            return Response({'error': 'Request is not pending'}, status=400)
        
        encashment.status = 'APPROVED'
        encashment.approved_by = request.user
        encashment.approved_at = timezone.now()
        encashment.save()
        
        return Response({'message': 'Encashment approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def process(self, request, pk=None):
        """Mark encashment as processed"""
        encashment = self.get_object()
        
        if encashment.status != 'APPROVED':
            return Response({'error': 'Request must be approved first'}, status=400)
        
        encashment.status = 'PROCESSED'
        encashment.processed_at = timezone.now()
        encashment.save()
        
        return Response({'message': 'Encashment processed'})

@action(detail=False, methods=['get'])
def dashboard_summary(self, request):
    """Get comprehensive dashboard summary"""
    try:
        employee = request.user.employee_profile
        current_year = date.today().year
        
        balances = LeaveBalance.objects.filter(
            employee=employee,
            year=current_year
        ).select_related('leave_type')
        
        return Response({
            'balances': LeaveBalanceSerializer(balances, many=True).data,
            'pending_requests': self._get_pending_count(employee),
            'upcoming_leaves': self._get_upcoming_leaves(employee),
            'team_on_leave': self._get_team_on_leave(employee),
            'utilization_trend': self._get_utilization_trend(employee)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)