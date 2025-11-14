from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, AssetCategoryViewSet, AssetAssignmentViewSet

router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'categories', AssetCategoryViewSet, basename='asset-category')
router.register(r'history', AssetAssignmentViewSet, basename='asset-history')

urlpatterns = [
    path('', include(router.urls)),
]