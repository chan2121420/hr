from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import Asset, AssetCategory, AssetAssignment
from .serializers import (
    AssetSerializer, 
    AssetCategorySerializer, 
    AssetAssignmentSerializer,
    AssetCheckOutSerializer,
    AssetCheckInSerializer
)
from .filters import AssetFilter
from apps.employees.models import Employee
from apps.accounts.permissions import IsAdminOrReadOnly

class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAdminOrReadOnly]

class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all().select_related(
        'category', 
        'current_employee__user'
    ).prefetch_related('assignments')
    serializer_class = AssetSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AssetFilter

    @action(detail=True, methods=['post'], serializer_class=AssetCheckOutSerializer)
    def assign(self, request, pk=None):
        asset = self.get_object()
        serializer = AssetCheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if asset.status != 'IN_STOCK':
            return Response(
                {"error": "Asset is not available. Current status: " + asset.status}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            employee = Employee.objects.get(id=serializer.validated_data['employee_id'])
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        asset.status = 'ASSIGNED'
        asset.current_employee = employee
        asset.save()
        
        AssetAssignment.objects.create(
            asset=asset,
            employee=employee,
            assigned_by=request.user,
            condition_out=serializer.validated_data.get('condition_out', '')
        )
        
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], serializer_class=AssetCheckInSerializer)
    def check_in(self, request, pk=None):
        asset = self.get_object()
        serializer = AssetCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if asset.status != 'ASSIGNED':
            return Response(
                {"error": "Asset is not currently assigned."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        last_assignment = asset.assignments.first()
        if last_assignment:
            last_assignment.returned_date = timezone.now()
            last_assignment.condition_in = serializer.validated_data['condition_in']
            last_assignment.save()

        asset.status = 'IN_STOCK'
        asset.current_employee = None
        asset.save()
        
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

class AssetAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetAssignment.objects.all()
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsAdminUser]