import django_filters
from django.db.models import Q
from .models import Employee, Department, Designation


class DepartmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    code = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter()
    has_sub_departments = django_filters.BooleanFilter(
        method='filter_has_sub_departments'
    )
    min_employees = django_filters.NumberFilter(
        method='filter_min_employees'
    )
    
    class Meta:
        model = Department
        fields = ['name', 'code', 'is_active', 'location']
    
    def filter_has_sub_departments(self, queryset, name, value):
        if value:
            return queryset.filter(sub_departments__isnull=False).distinct()
        return queryset
    
    def filter_min_employees(self, queryset, name, value):
        return queryset.annotate(
            emp_count=django_filters.Count('employee')
        ).filter(emp_count__gte=value)


class EmployeeFilter(django_filters.FilterSet):
    # Basic filters
    name = django_filters.CharFilter(method='filter_name')
    employee_id = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(
        field_name='work_email',
        lookup_expr='icontains'
    )
    
    # Department filters
    department = django_filters.ModelChoiceFilter(queryset=Department.objects.all())
    department_name = django_filters.CharFilter(
        field_name='department__name',
        lookup_expr='icontains'
    )
    
    # Designation filters
    designation = django_filters.ModelChoiceFilter(queryset=Designation.objects.all())
    designation_title = django_filters.CharFilter(
        field_name='designation__title',
        lookup_expr='icontains'
    )
    designation_level = django_filters.NumberFilter(
        field_name='designation__level'
    )
    
    # Employment filters
    status = django_filters.MultipleChoiceFilter(
        choices=Employee.EmploymentStatus.choices
    )
    employment_type = django_filters.MultipleChoiceFilter(
        choices=Employee.EmploymentType.choices
    )
    
    # Date filters
    join_date_from = django_filters.DateFilter(
        field_name='join_date',
        lookup_expr='gte'
    )
    join_date_to = django_filters.DateFilter(
        field_name='join_date',
        lookup_expr='lte'
    )
    
    # Manager filter
    manager = django_filters.ModelChoiceFilter(
        queryset=Employee.objects.all()
    )
    has_manager = django_filters.BooleanFilter(
        field_name='manager',
        lookup_expr='isnull',
        exclude=True
    )
    
    # Location filters
    work_location = django_filters.ChoiceFilter(
        choices=[
            ('HEAD_OFFICE', 'Head Office'),
            ('BRANCH', 'Branch Office'),
            ('REMOTE', 'Remote'),
            ('HYBRID', 'Hybrid'),
        ]
    )
    
    # Special filters
    on_probation = django_filters.BooleanFilter(method='filter_on_probation')
    contract_expiring = django_filters.BooleanFilter(method='filter_contract_expiring')
    due_for_review = django_filters.BooleanFilter(method='filter_due_for_review')
    is_manager = django_filters.BooleanFilter(method='filter_is_manager')
    
    # Salary filters
    min_salary = django_filters.NumberFilter(
        field_name='current_salary',
        lookup_expr='gte'
    )
    max_salary = django_filters.NumberFilter(
        field_name='current_salary',
        lookup_expr='lte'
    )
    
    # Performance filter
    min_rating = django_filters.NumberFilter(
        field_name='performance_rating',
        lookup_expr='gte'
    )
    
    class Meta:
        model = Employee
        fields = [
            'status', 'employment_type', 'department',
            'designation', 'manager', 'work_location'
        ]
    
    def filter_name(self, queryset, name, value):
        """Filter by first name or last name"""
        return queryset.filter(
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value)
        )
    
    def filter_on_probation(self, queryset, name, value):
        """Filter employees currently on probation"""
        if value:
            from datetime import date
            return queryset.filter(
                status='PROBATION',
                probation_end_date__gte=date.today()
            )
        return queryset.exclude(status='PROBATION')
    
    def filter_contract_expiring(self, queryset, name, value):
        """Filter employees with contracts expiring in 30 days"""
        if value:
            from datetime import date, timedelta
            thirty_days = date.today() + timedelta(days=30)
            return queryset.filter(
                contract_end_date__lte=thirty_days,
                contract_end_date__gte=date.today()
            )
        return queryset
    
    def filter_due_for_review(self, queryset, name, value):
        """Filter employees due for performance review"""
        if value:
            from datetime import date
            return queryset.filter(
                next_review_date__lte=date.today()
            )
        return queryset
    
    def filter_is_manager(self, queryset, name, value):
        """Filter employees who are managers"""
        if value:
            return queryset.filter(subordinates__isnull=False).distinct()
        return queryset.filter(subordinates__isnull=True)