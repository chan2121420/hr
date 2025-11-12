from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import Company, Department
from .serializers import CompanySerializer, DepartmentSerializer

class CompanyViewSet(viewsets.ModelViewSet):
    """CRUD for companies"""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'registration_number', 'tax_number', 'city', 'country']
    ordering_fields = ['name', 'created_at']

class DepartmentViewSet(viewsets.ModelViewSet):
    """CRUD for departments"""
    queryset = Department.objects.select_related('company', 'manager')
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'company__name', 'manager__first_name', 'manager__last_name']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Optionally filter by company via query params"""
        queryset = super().get_queryset()
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset
