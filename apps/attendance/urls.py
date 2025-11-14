from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShiftViewSet, AttendanceRecordViewSet

router = DefaultRouter()
router.register(r'shifts', ShiftViewSet, basename='shift')
router.register(r'records', AttendanceRecordViewSet, basename='attendance-record')

urlpatterns = [
    path('', include(router.urls)),
]