from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Avg, Sum, F, DecimalField
from django.db.models.functions import TruncMonth, Cast
from django.utils import timezone
from datetime import timedelta

# Import models from your other apps
from apps.employees.models import Employee, Department
from apps.leaves.models import LeaveRequest
from apps.payroll.models import Payslip
from apps.performance.models import PerformanceReview  # <-- THIS LINE IS FIXED

from .serializers import (
    KeyValueSerializer, 
    PayrollSummarySerializer, 
    LeaveBreakdownSerializer,
    PerformanceDistributionSerializer
)

class DashboardSummaryAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        total_employees = Employee.objects.filter(status='ACTIVE').count()
        
        pending_leaves = LeaveRequest.objects.filter(status='PENDING').count()
        
        today = timezone.now().date()
        recent_hires = Employee.objects.filter(
            join_date__gte=today - timedelta(days=30)
        ).count()
        
        upcoming_reviews = PerformanceReview.objects.filter(  # <-- THIS LINE IS FIXED
            status='PENDING', 
            due_date__gte=today,
            due_date__lte=today + timedelta(days=30)
        ).count()

        data = {
            "total_employees": total_employees,
            "pending_leaves": pending_leaves,
            "recent_hires": recent_hires,
            "upcoming_reviews": upcoming_reviews
        }
        return Response(data)

class HeadcountReportAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        headcount_by_dept = Department.objects.annotate(
            value=Count('employee', filter=F('employee__status')=='ACTIVE')
        ).values('name', 'value')
        
        headcount_by_type = Employee.objects.filter(status='ACTIVE') \
            .values(key=F('employment_type')) \
            .annotate(value=Count('id'))
            
        data = {
            "by_department": KeyValueSerializer(headcount_by_dept, many=True, context={'key': 'name'}).data,
            "by_employment_type": KeyValueSerializer(headcount_by_type, many=True).data,
        }
        return Response(data)

class EmployeeTurnoverAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        year = int(request.query_params.get('year', timezone.now().year))
        
        start_of_year = timezone.datetime(year, 1, 1).date()
        end_of_year = timezone.datetime(year, 12, 31).date()

        employees_started = Employee.objects.filter(
            join_date__gte=start_of_year,
            join_date__lte=end_of_year
        ).count()

        employees_left = Employee.objects.filter(
            termination_date__gte=start_of_year,
            termination_date__lte=end_of_year
        ).count()

        avg_headcount = (employees_started + Employee.objects.filter(status='ACTIVE').count()) / 2
        
        turnover_rate = 0
        if avg_headcount > 0:
            turnover_rate = (employees_left / avg_headcount) * 100

        data = {
            "year": year,
            "new_hires": employees_started,
            "terminations": employees_left,
            "average_headcount": round(avg_headcount, 2),
            "turnover_rate_percent": round(turnover_rate, 2)
        }
        return Response(data)

class LeaveAnalyticsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        year = int(request.query_params.get('year', timezone.now().year))

        leave_breakdown = LeaveRequest.objects.filter(
            status='APPROVED',
            start_date__year=year
        ).values(leave_type=F('leave_type__name')) \
         .annotate(days_taken=Sum(F('end_date') - F('start_date')))
        
        serializer = LeaveBreakdownSerializer(leave_breakdown, many=True)
        return Response(serializer.data)

class PayrollAnalyticsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        month = int(request.query_params.get('month', timezone.now().month))
        year = int(request.query_params.get('year', timezone.now().year))

        payslips = Payslip.objects.filter(pay_period_month=month, pay_period_year=year)
        
        summary = payslips.aggregate(
            total_payroll=Sum('net_pay'),
            total_earnings=Sum('total_earnings'),
            total_deductions=Sum('total_deductions'),
            employee_count=Count('id')
        )
        
        serializer = PayrollSummarySerializer(summary)
        return Response(serializer.data)

class PerformanceAnalyticsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        
        avg_by_dept = Employee.objects.filter(status='ACTIVE') \
            .annotate(avg_rating=Avg('reviews__overall_rating')) \
            .values(key=F('department__name'), value=F('avg_rating'))
            
        distribution = PerformanceReview.objects.filter(status='COMPLETED') \
            .values(rating=F('overall_rating')) \
            .annotate(count=Count('id')) \
            .order_by('rating')

        data = {
            "average_rating_by_department": KeyValueSerializer(avg_by_dept, many=True, context={'key': 'name', 'value': 'avg_rating'}).data,
            "overall_rating_distribution": PerformanceDistributionSerializer(distribution, many=True).data
        }
        return Response(data)