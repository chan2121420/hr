from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import SalaryComponent, EmployeeSalary, Payslip
from .serializers import (
    SalaryComponentSerializer,
    EmployeeSalarySerializer,
    PayslipSerializer,
    PayrollRunSerializer
)
from .utils import generate_payslip_for_employee
from apps.employees.models import Employee
from apps.accounts.permissions import IsAdminOrReadOnly
import calendar
import datetime

class SalaryComponentViewSet(viewsets.ModelViewSet):
    queryset = SalaryComponent.objects.all()
    serializer_class = SalaryComponentSerializer
    permission_classes = [IsAdminOrReadOnly]

class EmployeeSalaryViewSet(viewsets.ModelViewSet):
    queryset = EmployeeSalary.objects.all()
    serializer_class = EmployeeSalarySerializer
    permission_classes = [IsAdminUser]

class PayslipViewSet(viewsets.ModelViewSet):
    queryset = Payslip.objects.all().select_related('employee__user').prefetch_related('entries__component')
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payslip.objects.all()
        return Payslip.objects.filter(employee=user.employee_profile)

    @action(detail=False, methods=['post'], 
            permission_classes=[IsAdminUser], 
            serializer_class=PayrollRunSerializer)
    def run_payroll(self, request):
        serializer = PayrollRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        month = serializer.validated_data['month']
        year = serializer.validated_data['year']
        
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime.date(year, month, 1)
        end_date = datetime.date(year, month, last_day)
        
        active_employees = Employee.objects.filter(status='ACTIVE')
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for employee in active_employees:
            try:
                generate_payslip_for_employee(employee, start_date, end_date)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Failed for {employee}: {str(e)}")
                
        return Response({
            "message": "Payroll run completed.",
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }, status=status.HTTP_200_OK)