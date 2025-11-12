from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import DashboardWidget, Report
from .serializers import DashboardWidgetSerializer, ReportSerializer

class DashboardWidgetViewSet(viewsets.ModelViewSet):
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'widget_type', 'data_source']
    ordering_fields = ['order', 'created_at']

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('created_by')
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'report_type', 'description']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        """Optionally filter by created_by or report_type via query params"""
        queryset = super().get_queryset()
        created_by = self.request.query_params.get('created_by')
        report_type = self.request.query_params.get('report_type')
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        return queryset
