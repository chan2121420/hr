from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', include('apps.core.urls')), 
    
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/employees/', include('apps.employees.urls')),
    path('api/leaves/', include('apps.leaves.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
    path('api/payroll/', include('apps.payroll.urls')),
    path('api/performance/', include('apps.performance.urls')),
    path('api/recruitment/', include('apps.recruitment.urls')),
    path('api/training/', include('apps.training.urls')),
    path('api/assets/', include('apps.assets.urls')),
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)