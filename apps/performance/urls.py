from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GoalViewSet, PerformanceReviewViewSet

router = DefaultRouter()
router.register(r'goals', GoalViewSet, basename='goal')
router.register(r'reviews', PerformanceReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
]