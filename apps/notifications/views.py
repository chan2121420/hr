from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    """
    CRUD for system notifications
    """
    queryset = Notification.objects.select_related('recipient')
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['created_at', 'is_read']
    search_fields = ['title', 'message']

    def get_queryset(self):
        """Limit to notifications of the current user"""
        user = self.request.user
        return self.queryset.filter(recipient=user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        if notification.is_read:
            return Response({'message': 'Notification already read'}, status=status.HTTP_400_BAD_REQUEST)
        
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response({'message': 'Notification marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for the user"""
        user = request.user
        updated_count = Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'message': f'{updated_count} notifications marked as read'})
