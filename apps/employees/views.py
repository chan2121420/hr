from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    Department, Designation, Employee, EmergencyContact,
    BankDetails, EmployeeDocument, Dependent, EmployeeNote
)
from .serializers import (
    DepartmentSerializer, DepartmentDetailSerializer,
    DesignationSerializer, DesignationDetailSerializer,
    EmployeeSerializer, EmployeeDetailSerializer, EmployeeCreateSerializer,
    EmergencyContactSerializer, BankDetailsSerializer,
    EmployeeDocumentSerializer, DependentSerializer, EmployeeNoteSerializer
)
from .filters import EmployeeFilter, DepartmentFilter

class DepartmentViewSet(viewsets.ModelViewSet):
    """Enhanced Department ViewSet with analytics"""
    queryset = Department.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DepartmentFilter
    search_fields = ['name', 'code', 'location']
    ordering_fields = ['name', 'created_at', 'employee_count']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DepartmentDetailSerializer
        return DepartmentSerializer

    def get_queryset(self):
        queryset = Department.objects.prefetch_related('employee_set', 'sub_departments')
        
        # Filter by active status
        if self.request.query_params.get('is_active'):
            is_active = self.request.query_params.get('is_active').lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        return queryset

    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """Get all employees in department"""
        department = self.get_object()
        include_sub = request.query_params.get('include_sub', 'true').lower() == 'true'
        
        employees = department.get_all_employees(include_sub_departments=include_sub)
        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        """Get department hierarchy"""
        department = self.get_object()
        
        def build_hierarchy(dept):
            return {
                'id': str(dept.id),
                'name': dept.name,
                'code': dept.code,
                'employee_count': dept.employee_count,
                'head': dept.head.full_name if dept.head else None,
                'sub_departments': [
                    build_hierarchy(sub) 
                    for sub in dept.sub_departments.filter(is_active=True)
                ]
            }
        
        return Response(build_hierarchy(department))

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get department analytics"""
        department = self.get_object()
        employees = department.employee_set.filter(status='ACTIVE')
        
        data = {
            'total_employees': employees.count(),
            'by_employment_type': dict(
                employees.values_list('employment_type').annotate(count=Count('id'))
            ),
            'by_designation': list(
                employees.values('designation__title').annotate(count=Count('id'))
            ),
            'average_tenure': round(
                sum(e.tenure_years for e in employees) / max(employees.count(), 1), 2
            ),
            'average_salary': department.get_average_salary(),
            'total_payroll': department.get_total_payroll_cost(),
            'budget_utilization': department.budget_utilization_percentage,
            'gender_distribution': dict(
                employees.values_list('user__profile__gender').annotate(count=Count('id'))
            ),
        }
        return Response(data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of all departments"""
        departments = self.get_queryset().filter(is_active=True)
        
        summary = {
            'total_departments': departments.count(),
            'total_employees': Employee.objects.filter(status='ACTIVE').count(),
            'departments': [
                {
                    'id': str(dept.id),
                    'name': dept.name,
                    'employee_count': dept.employee_count,
                    'budget_utilization': dept.budget_utilization_percentage,
                }
                for dept in departments
            ]
        }
        return Response(summary)


class DesignationViewSet(viewsets.ModelViewSet):
    """Enhanced Designation ViewSet"""
    queryset = Designation.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'code']
    ordering_fields = ['level', 'title', 'created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DesignationDetailSerializer
        return DesignationSerializer

    def get_queryset(self):
        queryset = Designation.objects.all()
        
        if self.request.query_params.get('is_active'):
            is_active = self.request.query_params.get('is_active').lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        return queryset

    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """Get all employees with this designation"""
        designation = self.get_object()
        employees = designation.employee_set.filter(status='ACTIVE')
        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def career_path(self, request, pk=None):
        """Get career progression path"""
        designation = self.get_object()
        
        path = []
        current = designation
        while current and len(path) < 10:
            path.append({
                'id': str(current.id),
                'title': current.title,
                'level': current.level,
                'salary_range': current.salary_range_display,
            })
            current = current.next_level_designation
        
        return Response(path)


class EmployeeViewSet(viewsets.ModelViewSet):
    """Enhanced Employee ViewSet with comprehensive features"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EmployeeFilter
    search_fields = ['user__first_name', 'user__last_name', 'employee_id', 'work_email']
    ordering_fields = ['join_date', 'employee_id', 'created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = Employee.objects.select_related(
            'user__profile', 'department', 'designation', 'manager__user', 'bank_details'
        ).prefetch_related('emergency_contacts', 'documents', 'dependents')
        
        # Admins see all, others see limited
        if not user.is_staff:
            # Regular users see themselves, their team, and public info
            queryset = queryset.filter(
                Q(user=user) | 
                Q(manager__user=user) |
                Q(department=user.employee_profile.department, status='ACTIVE')
            )
        
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == 'create':
            return EmployeeCreateSerializer
        elif self.action == 'retrieve':
            return EmployeeDetailSerializer
        return EmployeeSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's employee profile"""
        try:
            employee = request.user.employee_profile
            serializer = EmployeeDetailSerializer(employee)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)

    @action(detail=False, methods=['get'])
    def my_team(self, request):
        """Get current user's team members"""
        try:
            employee = request.user.employee_profile
            if not employee.department:
                return Response([])
            
            team = Employee.objects.filter(
                department=employee.department,
                status='ACTIVE'
            ).exclude(id=employee.id)
            
            serializer = EmployeeSerializer(team, many=True)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response([])

    @action(detail=False, methods=['get'])
    def my_subordinates(self, request):
        """Get current user's direct subordinates"""
        try:
            employee = request.user.employee_profile
            subordinates = employee.subordinates.filter(status='ACTIVE')
            serializer = EmployeeSerializer(subordinates, many=True)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response([])

    @action(detail=True, methods=['get'])
    def reporting_chain(self, request, pk=None):
        """Get employee's reporting chain"""
        employee = self.get_object()
        chain = employee.get_reporting_chain()
        
        data = [
            {
                'id': str(mgr.id),
                'name': mgr.full_name,
                'designation': mgr.designation.title if mgr.designation else None,
                'department': mgr.department.name if mgr.department else None,
            }
            for mgr in chain
        ]
        return Response(data)

    @action(detail=True, methods=['get'])
    def subordinates_tree(self, request, pk=None):
        """Get employee's subordinate tree"""
        employee = self.get_object()
        
        def build_tree(emp):
            return {
                'id': str(emp.id),
                'name': emp.full_name,
                'designation': emp.designation.title if emp.designation else None,
                'subordinates': [
                    build_tree(sub) 
                    for sub in emp.subordinates.filter(status='ACTIVE')
                ]
            }
        
        return Response(build_tree(employee))

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def confirm_probation(self, request, pk=None):
        """Confirm employee after probation"""
        employee = self.get_object()
        
        if employee.status != 'PROBATION':
            return Response(
                {'error': 'Employee not on probation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        employee.status = 'ACTIVE'
        employee.confirmation_date = date.today()
        employee.save()
        
        return Response({'message': 'Employee confirmed successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def terminate(self, request, pk=None):
        """Terminate employee"""
        employee = self.get_object()
        
        employee.status = 'TERMINATED'
        employee.termination_date = request.data.get('termination_date', date.today())
        employee.termination_reason = request.data.get('reason', '')
        employee.termination_type = request.data.get('type', 'INVOLUNTARY')
        employee.eligible_for_rehire = request.data.get('eligible_for_rehire', False)
        employee.save()
        
        return Response({'message': 'Employee terminated'})

    @action(detail=True, methods=['get', 'post'])
    def emergency_contacts(self, request, pk=None):
        """Manage emergency contacts"""
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

    @action(detail=True, methods=['get', 'put', 'patch'])
    def bank_details(self, request, pk=None):
        """Manage bank details"""
        employee = self.get_object()
        
        try:
            bank_details = employee.bank_details
        except BankDetails.DoesNotExist:
            bank_details = BankDetails.objects.create(employee=employee)
        
        if request.method in ['PUT', 'PATCH']:
            serializer = BankDetailsSerializer(
                bank_details,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = BankDetailsSerializer(bank_details)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def documents(self, request, pk=None):
        """Manage employee documents"""
        employee = self.get_object()
        
        if request.method == 'POST':
            serializer = EmployeeDocumentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(employee=employee, uploaded_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        documents = employee.documents.all()
        doc_type = request.query_params.get('type')
        if doc_type:
            documents = documents.filter(document_type=doc_type)
        
        serializer = EmployeeDocumentSerializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def dependents(self, request, pk=None):
        """Manage dependents"""
        employee = self.get_object()
        
        if request.method == 'POST':
            serializer = DependentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(employee=employee)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        dependents = employee.dependents.all()
        serializer = DependentSerializer(dependents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAdminUser])
    def notes(self, request, pk=None):
        """Manage internal notes"""
        employee = self.get_object()
        
        if request.method == 'POST':
            serializer = EmployeeNoteSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(employee=employee, created_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        notes = employee.internal_notes.all()
        serializer = EmployeeNoteSerializer(notes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get employee statistics"""
        employees = Employee.objects.filter(status='ACTIVE')
        
        stats = {
            'total_employees': employees.count(),
            'by_status': dict(
                Employee.objects.values_list('status').annotate(count=Count('id'))
            ),
            'by_department': list(
                employees.values('department__name').annotate(count=Count('id'))
            ),
            'by_employment_type': dict(
                employees.values_list('employment_type').annotate(count=Count('id'))
            ),
            'average_tenure': round(
                sum(e.tenure_years for e in employees) / max(employees.count(), 1), 2
            ),
            'on_probation': employees.filter(status='PROBATION').count(),
            'expiring_contracts': employees.filter(
                contract_end_date__lte=date.today() + timedelta(days=30),
                contract_end_date__gte=date.today()
            ).count(),
            'due_for_review': employees.filter(
                next_review_date__lte=date.today()
            ).count(),
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def birthdays(self, request):
        """Get upcoming birthdays"""
        month = int(request.query_params.get('month', date.today().month))
        
        employees = Employee.objects.filter(
            status='ACTIVE',
            user__profile__date_of_birth__month=month
        ).select_related('user__profile')
        
        data = [
            {
                'id': str(emp.id),
                'name': emp.full_name,
                'date': emp.user.profile.date_of_birth,
                'department': emp.department.name if emp.department else None,
            }
            for emp in employees
            if hasattr(emp.user, 'profile') and emp.user.profile.date_of_birth
        ]
        
        return Response(sorted(data, key=lambda x: x['date'].day))

    @action(detail=False, methods=['get'])
    def anniversaries(self, request):
        """Get work anniversaries"""
        month = int(request.query_params.get('month', date.today().month))
        
        employees = Employee.objects.filter(
            status='ACTIVE',
            join_date__month=month
        )
        
        data = [
            {
                'id': str(emp.id),
                'name': emp.full_name,
                'join_date': emp.join_date,
                'years': emp.tenure_years,
                'department': emp.department.name if emp.department else None,
            }
            for emp in employees
        ]
        
        return Response(sorted(data, key=lambda x: x['join_date'].day))

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def org_chart(self, request):
        """Get organization chart data"""
        # Get all executives (no manager)
        executives = Employee.objects.filter(
            status='ACTIVE',
            manager__isnull=True
        )
        
        def build_org_chart(employee):
            return {
                'id': str(employee.id),
                'name': employee.full_name,
                'designation': employee.designation.title if employee.designation else None,
                'department': employee.department.name if employee.department else None,
                'subordinates': [
                    build_org_chart(sub)
                    for sub in employee.subordinates.filter(status='ACTIVE')
                ]
            }
        
        chart = [build_org_chart(exec) for exec in executives]
        return Response(chart)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def org_chart(self, request):
        """
        Optimized Org Chart: Fetches all employees in 1 query 
        and builds tree in memory.
        """
        all_employees = Employee.objects.filter(status='ACTIVE').select_related(
            'designation', 'department', 'manager'
        )

        subordinates_map = {}
        executives = []

        for emp in all_employees:
            if emp.manager_id:
                if emp.manager_id not in subordinates_map:
                    subordinates_map[emp.manager_id] = []
                subordinates_map[emp.manager_id].append(emp)
            else:
                executives.append(emp)

        def build_org_chart_memory(employee):
            # Get subs from memory map, default to empty list
            subs = subordinates_map.get(employee.id, [])
            
            return {
                'id': str(employee.id),
                'name': employee.full_name,
                'designation': employee.designation.title if employee.designation else None,
                'department': employee.department.name if employee.department else None,
                'subordinates': [
                    build_org_chart_memory(sub) for sub in subs
                ]
            }

        chart = [build_org_chart_memory(exec) for exec in executives]
        return Response(chart)