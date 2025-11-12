from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import Asset, AssetCategory, AssetAssignment
from .serializers import AssetSerializer, AssetCategorySerializer, AssetAssignmentSerializer

class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related('category')
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'asset_tag', 'category__name', 'manufacturer', 'model', 'serial_number']
    ordering_fields = ['asset_tag', 'name', 'created_at']

class AssetAssignmentViewSet(viewsets.ModelViewSet):
    queryset = AssetAssignment.objects.select_related('asset', 'employee', 'assigned_by')
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['asset__name', 'employee__first_name', 'employee__last_name', 'assigned_by__first_name', 'assigned_by__last_name']
    ordering_fields = ['assigned_date', 'expected_return_date', 'created_at']

    def get_queryset(self):
        """Filter assignments by asset or employee via query params"""
        queryset = super().get_queryset()
        asset_id = self.request.query_params.get('asset')
        employee_id = self.request.query_params.get('employee')
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return queryset
