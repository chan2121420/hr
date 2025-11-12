import django_filters
from .models import Employee

class EmployeeFilter(django_filters.FilterSet):
    """
    Filter employees by department, position, manager, employment type, and active status
    """
    department = django_filters.NumberFilter(field_name='department__id')
    position = django_filters.NumberFilter(field_name='position__id')
    manager = django_filters.NumberFilter(field_name='manager__id')
    employment_type = django_filters.ChoiceFilter(choices=Employee.EMPLOYMENT_TYPE)
    is_active = django_filters.BooleanFilter()

    # Optional: filter by name or email (partial match)
    name = django_filters.CharFilter(method='filter_by_name')
    email = django_filters.CharFilter(field_name='work_email', lookup_expr='icontains')

    class Meta:
        model = Employee
        fields = ['department', 'position', 'manager', 'employment_type', 'is_active', 'name', 'email']

    def filter_by_name(self, queryset, name, value):
        """
        Allow filtering by first_name or last_name containing the value
        """
        return queryset.filter(
            models.Q(first_name__icontains=value) | models.Q(last_name__icontains=value)
        )
