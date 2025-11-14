import django_filters
from .models import Employee

class EmployeeFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='user__first_name', 
        lookup_expr='icontains'
    )
    department = django_filters.CharFilter(
        field_name='department__name', 
        lookup_expr='icontains'
    )

    class Meta:
        model = Employee
        fields = ['status', 'employment_type', 'department', 'name']