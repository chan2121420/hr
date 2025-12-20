from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, DesignationViewSet, EmployeeViewSet

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'designations', DesignationViewSet, basename='designation')
router.register(r'employees', EmployeeViewSet, basename='employee')

app_name = 'employees'

urlpatterns = [
    # API Routes
    path('api/', include(router.urls)),
    
    # Additional custom endpoints
    path('api/employees/<uuid:pk>/emergency-contacts/', 
         EmployeeViewSet.as_view({'get': 'emergency_contacts', 'post': 'emergency_contacts'}),
         name='employee-emergency-contacts'),
    
    path('api/employees/<uuid:pk>/bank-details/',
         EmployeeViewSet.as_view({'get': 'bank_details', 'put': 'bank_details', 'patch': 'bank_details'}),
         name='employee-bank-details'),
    
    path('api/employees/<uuid:pk>/documents/',
         EmployeeViewSet.as_view({'get': 'documents', 'post': 'documents'}),
         name='employee-documents'),
    
    path('api/employees/<uuid:pk>/dependents/',
         EmployeeViewSet.as_view({'get': 'dependents', 'post': 'dependents'}),
         name='employee-dependents'),
    
    path('api/employees/<uuid:pk>/notes/',
         EmployeeViewSet.as_view({'get': 'notes', 'post': 'notes'}),
         name='employee-notes'),
    
    path('api/employees/<uuid:pk>/reporting-chain/',
         EmployeeViewSet.as_view({'get': 'reporting_chain'}),
         name='employee-reporting-chain'),
    
    path('api/employees/<uuid:pk>/subordinates-tree/',
         EmployeeViewSet.as_view({'get': 'subordinates_tree'}),
         name='employee-subordinates-tree'),
    
    path('api/employees/<uuid:pk>/confirm-probation/',
         EmployeeViewSet.as_view({'post': 'confirm_probation'}),
         name='employee-confirm-probation'),
    
    path('api/employees/<uuid:pk>/terminate/',
         EmployeeViewSet.as_view({'post': 'terminate'}),
         name='employee-terminate'),
    
    # Statistics and reports
    path('api/employees/statistics/',
         EmployeeViewSet.as_view({'get': 'statistics'}),
         name='employee-statistics'),
    
    path('api/employees/birthdays/',
         EmployeeViewSet.as_view({'get': 'birthdays'}),
         name='employee-birthdays'),
    
    path('api/employees/anniversaries/',
         EmployeeViewSet.as_view({'get': 'anniversaries'}),
         name='employee-anniversaries'),
    
    path('api/employees/org-chart/',
         EmployeeViewSet.as_view({'get': 'org_chart'}),
         name='employee-org-chart'),
    
    # Department specific
    path('api/departments/<uuid:pk>/employees/',
         DepartmentViewSet.as_view({'get': 'employees'}),
         name='department-employees'),
    
    path('api/departments/<uuid:pk>/hierarchy/',
         DepartmentViewSet.as_view({'get': 'hierarchy'}),
         name='department-hierarchy'),
    
    path('api/departments/<uuid:pk>/analytics/',
         DepartmentViewSet.as_view({'get': 'analytics'}),
         name='department-analytics'),
    
    path('api/departments/summary/',
         DepartmentViewSet.as_view({'get': 'summary'}),
         name='department-summary'),
    
    # Designation specific
    path('api/designations/<uuid:pk>/employees/',
         DesignationViewSet.as_view({'get': 'employees'}),
         name='designation-employees'),
    
    path('api/designations/<uuid:pk>/career-path/',
         DesignationViewSet.as_view({'get': 'career_path'}),
         name='designation-career-path'),
]