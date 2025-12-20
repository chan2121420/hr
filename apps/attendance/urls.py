from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ShiftViewSet, AttendanceRecordViewSet, AttendanceExceptionViewSet,
    AttendanceSummaryViewSet, PublicHolidayViewSet
)

router = DefaultRouter()
router.register(r'shifts', ShiftViewSet, basename='shift')
router.register(r'records', AttendanceRecordViewSet, basename='attendance-record')
router.register(r'exceptions', AttendanceExceptionViewSet, basename='attendance-exception')
router.register(r'summaries', AttendanceSummaryViewSet, basename='attendance-summary')
router.register(r'holidays', PublicHolidayViewSet, basename='public-holiday')

app_name = 'attendance'

urlpatterns = [
    path('api/', include(router.urls)),
]