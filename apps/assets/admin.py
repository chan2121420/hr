from django.contrib import admin
from .models import Asset, AssetCategory, AssetAssignment

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class AssetAssignmentInline(admin.TabularInline):
    model = AssetAssignment
    extra = 0
    readonly_fields = (
        'employee', 
        'assigned_by', 
        'assigned_date', 
        'returned_date', 
        'condition_out', 
        'condition_in'
    )
    can_delete = False
    ordering = ['-assigned_date']

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'asset_tag', 
        'category', 
        'status', 
        'current_employee', 
        'purchase_date'
    )
    list_filter = ('status', 'category', 'purchase_date')
    search_fields = ('name', 'serial_number', 'asset_tag', 'current_employee__user__email')
    readonly_fields = ('current_employee', 'status')
    inlines = [AssetAssignmentInline]