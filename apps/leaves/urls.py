from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveTypeViewSet, 
    HolidayViewSet, 
    LeaveBalanceViewSet,
    LeaveRequestViewSet,
    LeaveEncashmentViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'types', LeaveTypeViewSet, basename='leave-type')
router.register(r'holidays', HolidayViewSet, basename='holiday')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'requests', LeaveRequestViewSet, basename='leave-request')
router.register(r'encashments', LeaveEncashmentViewSet, basename='leave-encashment')

app_name = 'leaves'

urlpatterns = [
    path('', include(router.urls)),
]