from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend

from .models import Department, Designation, Employee, EmergencyContact, BankDetails, EmployeeDocument
from .serializers import (
    DepartmentSerializer, 
    DesignationSerializer, 
    EmployeeSerializer,
    EmployeeCreateSerializer,
    EmergencyContactSerializer, 
    BankDetailsSerializer, 
    EmployeeDocumentSerializer
)
from .filters import EmployeeFilter
from apps.accounts.permissions import IsAdminOrReadOnly

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminOrReadOnly]

class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    permission_classes = [IsAdminOrReadOnly]

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().select_related(
        'user__profile', 
        'department', 
        'designation', 
        'manager__user', 
        'bank_details'
    ).prefetch_related(
        'emergency_contacts', 
        'documents'
    )
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmployeeFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return EmployeeCreateSerializer
        return EmployeeSerializer

    @action(detail=True, methods=['get', 'post'], serializer_class=EmergencyContactSerializer)
    def contacts(self, request, pk=None):
        employee = self.get_object()
        if request.method == 'POST':
            serializer = EmergencyContactSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(employee=employee)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        contacts = employee.emergency_contacts.all()
        serializer = EmergencyContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'put', 'patch'], serializer_class=BankDetailsSerializer)
    def bank_details(self, request, pk=None):
        employee = self.get_object()
        bank_details = employee.bank_details
        
        if request.method in ['PUT', 'PATCH']:
            serializer = BankDetailsSerializer(bank_details, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = BankDetailsSerializer(bank_details)
        return Response(serializer.data)