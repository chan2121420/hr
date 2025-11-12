from rest_framework import serializers
from .models import Asset, AssetCategory, AssetAssignment

class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = '__all__'

class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    current_assignment = serializers.SerializerMethodField()
    
    class Meta:
        model = Asset
        fields = '__all__'
    
    def get_current_assignment(self, obj):
        assignment = obj.assignments.filter(status='active').first()
        if assignment:
            return {
                'employee_name': assignment.employee.get_full_name(),
                'assigned_date': assignment.assigned_date
            }
        return None

class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    
    class Meta:
        model = AssetAssignment
        fields = '__all__'
