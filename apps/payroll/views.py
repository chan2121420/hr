from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import (
    PayrollComponent, EmployeePayrollComponent,
    PayrollPeriod, Payslip, PayslipComponent,
    LoanAdvance
)
from .serializers import (
    PayrollComponentSerializer, EmployeePayrollComponentSerializer,
    PayrollPeriodSerializer, PayslipSerializer, PayslipComponentSerializer,
    LoanAdvanceSerializer
)

# Payroll Components
class PayrollComponentViewSet(viewsets.ModelViewSet):
    queryset = PayrollComponent.objects.filter(is_active=True)
    serializer_class = PayrollComponentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'component_type']

class EmployeePayrollComponentViewSet(viewsets.ModelViewSet):
    queryset = EmployeePayrollComponent.objects.select_related('employee', 'component')
    serializer_class = EmployeePayrollComponentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'component', 'is_active']
    search_fields = ['employee__first_name', 'employee__last_name', 'component__name']
    ordering_fields = ['effective_from', 'amount']

# Payroll Periods
class PayrollPeriodViewSet(viewsets.ModelViewSet):
    queryset = PayrollPeriod.objects.prefetch_related('payslips')
    serializer_class = PayrollPeriodSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date']

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        period = self.get_object()
        if period.is_finalized:
            return Response({'error': 'Period already finalized'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Example: calculate totals
        total_gross = sum(p.gross_salary for p in period.payslips.all())
        total_deductions = sum(p.total_deductions for p in period.payslips.all())
        total_net = sum(p.net_salary for p in period.payslips.all())

        period.total_gross = total_gross
        period.total_deductions = total_deductions
        period.total_net = total_net
        period.is_finalized = True
        period.save()
        return Response({'message': 'Payroll period finalized successfully'})

# Payslips
class PayslipViewSet(viewsets.ModelViewSet):
    queryset = Payslip.objects.select_related('employee', 'period').prefetch_related('components')
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'period', 'is_paid']
    search_fields = ['employee__first_name', 'employee__last_name', 'period__name']
    ordering_fields = ['period', 'net_salary']

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        payslip = self.get_object()
        if payslip.is_paid:
            return Response({'error': 'Payslip already marked as paid'}, status=status.HTTP_400_BAD_REQUEST)
        
        payslip.is_paid = True
        payslip.payment_date = timezone.now().date()
        payslip.save()
        return Response({'message': 'Payslip marked as paid'})

# Loans / Advances
class LoanAdvanceViewSet(viewsets.ModelViewSet):
    queryset = LoanAdvance.objects.select_related('employee', 'approved_by')
    serializer_class = LoanAdvanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'status', 'loan_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'purpose']
    ordering_fields = ['start_date', 'amount']

    @action(detail=True, methods=['post'])
    def repay(self, request, pk=None):
        loan = self.get_object()
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        loan.amount_repaid += float(amount)
        if loan.amount_repaid >= loan.amount:
            loan.status = 'completed'
        else:
            loan.status = 'repaying'
        loan.save()
        return Response({'message': f'Loan repayment of {amount} recorded', 'balance': loan.balance})
