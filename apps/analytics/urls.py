from django.urls import path
from .views import (
    DashboardSummaryAPIView,
    HeadcountReportAPIView,
    EmployeeTurnoverAPIView,
    LeaveAnalyticsAPIView,
    PayrollAnalyticsAPIView,
    PerformanceAnalyticsAPIView
)

urlpatterns = [
    path('summary/', DashboardSummaryAPIView.as_view(), name='analytics-summary'),
    path('headcount/', HeadcountReportAPIView.as_view(), name='analytics-headcount'),
    path('turnover/', EmployeeTurnoverAPIView.as_view(), name='analytics-turnover'),
    path('leaves/', LeaveAnalyticsAPIView.as_view(), name='analytics-leaves'),
    path('payroll/', PayrollAnalyticsAPIView.as_view(), name='analytics-payroll'),
    path('performance/', PerformanceAnalyticsAPIView.as_view(), name='analytics-performance'),
]