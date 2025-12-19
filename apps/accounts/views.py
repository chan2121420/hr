from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.contrib.auth import logout, authenticate
from django.utils import timezone
from django.db.models import Q
import logging

from .models import CustomUser, Profile, Role
from .serializers import (
    UserSerializer, 
    ProfileSerializer, 
    RoleSerializer, 
    RegisterSerializer, 
    LoginSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdminOrReadOnly

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration
    """
    queryset = CustomUser.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create token for the new user
        token = Token.objects.create(user=user)
        
        # Log registration
        logger.info(f'New user registered: {user.email}')
        
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'token': token.key,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """
    API endpoint for user login
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        
        # Update last login IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        user.last_login_ip = ip
        user.last_login = timezone.now()
        user.save(update_fields=['last_login_ip', 'last_login'])
        
        # Log successful login
        logger.info(f'User logged in: {user.email} from {ip}')
        
        user_serializer = UserSerializer(user, context={'request': request})
        return Response({
            'token': token.key,
            'user': user_serializer.data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    API endpoint for user logout
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            logger.info(f'User logged out: {request.user.email}')
        except (AttributeError, Token.DoesNotExist):
            pass
        
        # Logout from session
        logout(request)
        
        return Response(
            {'message': 'Successfully logged out.'}, 
            status=status.HTTP_200_OK
        )


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users (Admin only)
    """
    queryset = CustomUser.objects.all().select_related('profile', 'role').order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    search_fields = ['email', 'first_name', 'last_name']
    filterset_fields = ['is_active', 'is_staff', 'role']

    def get_queryset(self):
        """
        Optionally filter users by query parameters
        """
        queryset = super().get_queryset()
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        """
        Activate a user account
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        logger.info(f'User activated: {user.email} by {request.user.email}')
        return Response({'message': 'User activated successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def deactivate(self, request, pk=None):
        """
        Deactivate a user account
        """
        user = self.get_object()
        if user == request.user:
            return Response(
                {'error': 'You cannot deactivate your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = False
        user.save()
        logger.info(f'User deactivated: {user.email} by {request.user.email}')
        return Response({'message': 'User deactivated successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reset_password(self, request, pk=None):
        """
        Reset user password (Admin only)
        """
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'New password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        # Delete existing token to force re-login
        Token.objects.filter(user=user).delete()
        
        logger.info(f'Password reset for user: {user.email} by {request.user.email}')
        return Response({'message': 'Password reset successfully'})


class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user profiles
    """
    queryset = Profile.objects.all().select_related('user')
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Filter profiles based on user permissions
        """
        if self.request.user.is_staff:
            return Profile.objects.all()
        return Profile.objects.filter(user=self.request.user)
    
    def get_object(self):
        """
        Allow 'me' as a shortcut to get the current user's profile
        """
        if self.kwargs.get('pk') == 'me':
            return self.request.user.profile
        return super().get_object()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get the current user's profile
        """
        serializer = self.get_serializer(request.user.profile)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def upload_avatar(self, request, pk=None):
        """
        Upload profile avatar
        """
        profile = self.get_object()
        
        if 'avatar' not in request.FILES:
            return Response(
                {'error': 'No avatar file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        profile.avatar = request.FILES['avatar']
        profile.save()
        
        return Response({
            'message': 'Avatar uploaded successfully',
            'avatar_url': request.build_absolute_uri(profile.avatar.url)
        })


class RoleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing roles
    """
    queryset = Role.objects.filter(is_active=True).order_by('name')
    serializer_class = RoleSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'description']

    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        Get all users with this role
        """
        role = self.get_object()
        users = role.users.filter(is_active=True)
        serializer = UserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """
    API endpoint for users to change their own password
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Both old_password and new_password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check old password
        if not user.check_password(old_password):
            return Response(
                {'error': 'Old password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate new password (add more validation as needed)
        if len(new_password) < 8:
            return Response(
                {'error': 'New password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Delete old token and create new one
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        
        logger.info(f'Password changed for user: {user.email}')
        
        return Response({
            'message': 'Password changed successfully',
            'token': token.key
        })