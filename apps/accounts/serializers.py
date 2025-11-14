from rest_framework import serializers
from .models import CustomUser, Profile, Role
from django.contrib.auth import authenticate

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'avatar', 
            'phone_number', 
            'bio', 
            'address_line_1', 
            'city', 
            'country', 
            'date_of_birth'
        ]

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    role = serializers.StringRelatedField()
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), 
        source='role', 
        write_only=True, 
        allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = [
            'id', 
            'username', 
            'email', 
            'first_name', 
            'last_name', 
            'role', 
            'role_id', 
            'profile', 
            'is_active', 
            'is_staff'
        ]
        read_only_fields = ['id', 'role']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        profile_serializer = ProfileSerializer(instance.profile, data=profile_data, partial=True)
        
        if profile_serializer.is_valid(raise_exception=True):
            profile_serializer.save()
        
        return super().update(instance, validated_data)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        min_length=8,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(label="Email", required=True)
    password = serializers.CharField(
        label="Password",
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            raise serializers.ValidationError(
                'Email and password are required.', 
                code='authorization'
            )

        user = authenticate(request=self.context.get('request'), username=email, password=password)

        if not user:
            raise serializers.ValidationError(
                'Invalid credentials. Please try again.', 
                code='authorization'
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                'User account is disabled.', 
                code='authorization'
            )
            
        data['user'] = user
        return data