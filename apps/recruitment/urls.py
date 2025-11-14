from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobPositionViewSet, CandidateViewSet, ApplicationViewSet, InterviewViewSet

router = DefaultRouter()
router.register(r'jobs', JobPositionViewSet, basename='job')
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'interviews', InterviewViewSet, basename='interview')

urlpatterns = [
    path('', include(router.urls)),
]