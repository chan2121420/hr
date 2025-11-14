import django_filters
from .models import Asset, AssetCategory

class AssetFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.ModelChoiceFilter(queryset=AssetCategory.objects.all())
    
    class Meta:
        model = Asset
        fields = ['status', 'category', 'name', 'serial_number', 'asset_tag']