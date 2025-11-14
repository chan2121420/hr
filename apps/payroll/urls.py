from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalaryComponentViewSet, EmployeeSalaryViewSet, PayslipViewSet

router = DefaultRouter()
router.register(r'components', SalaryComponentViewSet, basename='salary-component')
router.register(r'employee-salaries', EmployeeSalaryViewSet, basename='employee-salary')
router.register(r'payslips', PayslipViewSet, basename='payslip')

urlpatterns = [
    path('', include(router.urls)),
]