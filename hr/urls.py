# config/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()

# Register viewsets (you'll create these)
from apps.employees.views import EmployeeViewSet
from apps.tasks.views import TaskViewSet
from apps.attendance.views import AttendanceViewSet
from apps.leaves.views import LeaveRequestViewSet
from apps.payroll.views import PayslipViewSet

router.register('employees', EmployeeViewSet)
router.register('tasks', TaskViewSet)
router.register('attendance', AttendanceViewSet)
router.register('leaves', LeaveRequestViewSet)
router.register('payslips', PayslipViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]