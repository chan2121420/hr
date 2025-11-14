from rest_framework import serializers
from .models import Asset, AssetCategory, AssetAssignment
from apps.employees.serializers import EmployeeSerializer

class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'description']

class AssetAssignmentSerializer(serializers.ModelSerializer):
    employee = serializers.StringRelatedField()
    assigned_by = serializers.StringRelatedField()
    asset = serializers.StringRelatedField()

    class Meta:
        model = AssetAssignment
        fields = '__all__'

class AssetSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=AssetCategory.objects.all(), 
        source='category', 
        write_only=True
    )
    current_employee = EmployeeSerializer(read_only=True)
    assignments = AssetAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 
            'name', 
            'asset_tag',
            'serial_number', 
            'status', 
            'category', 
            'category_id',
            'purchase_date',
            'purchase_cost',
            'warranty_expiry_date',
            'current_employee',
            'assignments',
            'updated_at'
        ]
        read_only_fields = ['id', 'asset_tag', 'status', 'current_employee', 'assignments', 'updated_at']

class AssetCheckOutSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    condition_out = serializers.CharField(required=False, allow_blank=True)

class AssetCheckInSerializer(serializers.Serializer):
    condition_in = serializers.CharField(required=True)