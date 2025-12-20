import django_filters
from .models import AttendanceRecord, AttendanceException
from datetime import date, timedelta


class AttendanceRecordFilter(django_filters.FilterSet):
    # Date filters
    date = django_filters.DateFilter()
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    
    # Employee filters
    employee = django_filters.NumberFilter(field_name='employee__id')
    employee_name = django_filters.CharFilter(
        field_name='employee__user__first_name',
        lookup_expr='icontains'
    )
    department = django_filters.CharFilter(
        field_name='employee__department__name',
        lookup_expr='icontains'
    )
    
    # Status filters
    status = django_filters.MultipleChoiceFilter(
        choices=AttendanceRecord.AttendanceStatus.choices
    )
    
    # Shift filter
    shift = django_filters.UUIDFilter(field_name='shift__id')
    
    # Boolean filters
    is_late = django_filters.BooleanFilter()
    is_remote = django_filters.BooleanFilter()
    is_weekend_work = django_filters.BooleanFilter()
    is_public_holiday_work = django_filters.BooleanFilter()
    is_verified = django_filters.BooleanFilter()
    requires_verification = django_filters.BooleanFilter()
    
    # Special filters
    this_week = django_filters.BooleanFilter(method='filter_this_week')
    this_month = django_filters.BooleanFilter(method='filter_this_month')
    late_arrivals = django_filters.BooleanFilter(method='filter_late_arrivals')
    overtime_records = django_filters.BooleanFilter(method='filter_overtime')
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'date', 'status', 'employee', 'shift',
            'is_late', 'is_remote', 'is_verified'
        ]
    
    def filter_this_week(self, queryset, name, value):
        if value:
            today = date.today()
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return queryset.filter(date__range=[start_week, end_week])
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        if value:
            today = date.today()
            return queryset.filter(date__year=today.year, date__month=today.month)
        return queryset
    
    def filter_late_arrivals(self, queryset, name, value):
        if value:
            return queryset.filter(is_late=True)
        return queryset
    
    def filter_overtime(self, queryset, name, value):
        if value:
            return queryset.filter(status='OVERTIME')
        return queryset


class AttendanceExceptionFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name='employee__id')
    exception_date_from = django_filters.DateFilter(
        field_name='exception_date',
        lookup_expr='gte'
    )
    exception_date_to = django_filters.DateFilter(
        field_name='exception_date',
        lookup_expr='lte'
    )
    status = django_filters.MultipleChoiceFilter(
        choices=AttendanceException.ExceptionStatus.choices
    )
    exception_type = django_filters.MultipleChoiceFilter(
        choices=AttendanceException.ExceptionType.choices
    )
    is_urgent = django_filters.BooleanFilter()
    
    class Meta:
        model = AttendanceException
        fields = ['employee', 'status', 'exception_type', 'is_urgent']
