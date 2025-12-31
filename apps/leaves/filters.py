import django_filters
from .models import LeaveRequest, LeaveBalance
from datetime import date, timedelta


class LeaveRequestFilter(django_filters.FilterSet):
    # Employee filters
    employee = django_filters.UUIDFilter(field_name='employee__id')
    employee_name = django_filters.CharFilter(
        field_name='employee__user__first_name',
        lookup_expr='icontains'
    )
    department = django_filters.CharFilter(
        field_name='employee__department__name',
        lookup_expr='icontains'
    )
    
    # Leave type filter
    leave_type = django_filters.UUIDFilter(field_name='leave_type__id')
    leave_type_name = django_filters.CharFilter(
        field_name='leave_type__name',
        lookup_expr='icontains'
    )
    
    # Status filters
    status = django_filters.MultipleChoiceFilter(
        choices=LeaveRequest.LeaveStatus.choices
    )
    
    # Date filters
    start_date = django_filters.DateFilter()
    start_date_from = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='gte'
    )
    start_date_to = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='lte'
    )
    end_date_from = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='gte'
    )
    end_date_to = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='lte'
    )
    
    # Boolean filters
    is_half_day = django_filters.BooleanFilter()
    is_urgent = django_filters.BooleanFilter()
    is_emergency = django_filters.BooleanFilter()
    
    # Special filters
    is_current = django_filters.BooleanFilter(method='filter_is_current')
    is_upcoming = django_filters.BooleanFilter(method='filter_is_upcoming')
    this_month = django_filters.BooleanFilter(method='filter_this_month')
    requires_approval = django_filters.BooleanFilter(method='filter_requires_approval')
    
    class Meta:
        model = LeaveRequest
        fields = [
            'employee', 'leave_type', 'status',
            'start_date', 'is_half_day', 'is_urgent'
        ]
    
    def filter_is_current(self, queryset, name, value):
        """Filter currently active leaves"""
        if value:
            today = date.today()
            return queryset.filter(
                start_date__lte=today,
                end_date__gte=today,
                status='APPROVED'
            )
        return queryset
    
    def filter_is_upcoming(self, queryset, name, value):
        """Filter upcoming leaves (within 7 days)"""
        if value:
            today = date.today()
            week_from_now = today + timedelta(days=7)
            return queryset.filter(
                start_date__gte=today,
                start_date__lte=week_from_now,
                status='APPROVED'
            )
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        """Filter leaves in current month"""
        if value:
            today = date.today()
            return queryset.filter(
                start_date__year=today.year,
                start_date__month=today.month
            )
        return queryset
    
    def filter_requires_approval(self, queryset, name, value):
        """Filter leaves that require approval"""
        if value:
            return queryset.filter(status='PENDING')
        return queryset


class LeaveBalanceFilter(django_filters.FilterSet):
    # Employee filter
    employee = django_filters.UUIDFilter(field_name='employee__id')
    employee_name = django_filters.CharFilter(
        field_name='employee__user__first_name',
        lookup_expr='icontains'
    )
    
    # Leave type filter
    leave_type = django_filters.UUIDFilter(field_name='leave_type__id')
    leave_type_name = django_filters.CharFilter(
        field_name='leave_type__name',
        lookup_expr='icontains'
    )
    
    # Year filter
    year = django_filters.NumberFilter()
    
    # Special filters
    has_available_balance = django_filters.BooleanFilter(method='filter_has_balance')
    is_overdrawn = django_filters.BooleanFilter(method='filter_is_overdrawn')
    
    class Meta:
        model = LeaveBalance
        fields = ['employee', 'leave_type', 'year']
    
    def filter_has_balance(self, queryset, name, value):
        """Filter balances with available days"""
        if value:
            # This is a simplified filter - in production you'd calculate available balance
            return queryset.filter(used__lt=django_filters.F('total_allocated'))
        return queryset
    
    def filter_is_overdrawn(self, queryset, name, value):
        """Filter overdrawn balances"""
        if value:
            return queryset.filter(used__gt=django_filters.F('total_allocated'))
        return queryset