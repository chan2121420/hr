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
                {"error": f"Asset is not available. Current status: {asset.get_status_display()}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        employee_id = serializer.validated_data['employee_id']
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        # Create Assignment Record
        AssetAssignment.objects.create(
            asset=asset,
            employee=employee,
            assigned_by=request.user,
            assigned_date=timezone.now(),
            condition_out=serializer.validated_data.get('condition_out', asset.condition)
        )

        # Update Asset
        asset.status = 'ASSIGNED'
        asset.current_employee = employee
        asset.save()
        
        return Response(AssetSerializer(asset).data)

    @action(detail=True, methods=['post'], serializer_class=AssetCheckInSerializer)
    def return_asset(self, request, pk=None):
        asset = self.get_object()
        serializer = AssetCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if asset.status != 'ASSIGNED':
            return Response({"error": "Asset is not currently assigned."}, status=status.HTTP_400_BAD_REQUEST)

        # Close Assignment Record
        assignment = asset.assignments.filter(return_date__isnull=True).first()
        if assignment:
            assignment.return_date = timezone.now()
            assignment.condition_in = serializer.validated_data['condition_in']
            assignment.save()

        # Update Asset
        asset.status = 'IN_STOCK'
        asset.current_employee = None
        asset.condition = serializer.validated_data['condition_in']
        asset.save()

        return Response(AssetSerializer(asset).data)

class AssetAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssetAssignment.objects.all()
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsAdminUser]