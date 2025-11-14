from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainingCourseViewSet, CourseSessionViewSet, EnrollmentViewSet

router = DefaultRouter()
router.register(r'courses', TrainingCourseViewSet, basename='course')
router.register(r'sessions', CourseSessionViewSet, basename='session')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')

urlpatterns = [
    path('', include(router.urls)),
]