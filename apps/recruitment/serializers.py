from rest_framework import serializers
from .models import JobPosition, Candidate, Application, Interview
from apps.employees.serializers import EmployeeSerializer

class JobPositionSerializer(serializers.ModelSerializer):
    department = serializers.StringRelatedField()
    hiring_manager = serializers.StringRelatedField()
    application_count = serializers.IntegerField(source='applications.count', read_only=True)

    class Meta:
        model = JobPosition
        fields = [
            'id', 
            'title', 
            'department', 
            'hiring_manager', 
            'status', 
            'posted_at',
            'application_count',
            'description',
            'requirements'
        ]

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = '__all__'

class InterviewSerializer(serializers.ModelSerializer):
    interviewers = EmployeeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Interview
        fields = '__all__'
        read_only_fields = ['application']

class ApplicationSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer()
    job = JobPositionSerializer(read_only=True)
    job_id = serializers.PrimaryKeyRelatedField(
        queryset=JobPosition.objects.all(),
        source='job',
        write_only=True
    )
    interviews = InterviewSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 
            'candidate', 
            'job', 
            'job_id', 
            'stage', 
            'applied_at', 
            'updated_at',
            'interviews'
        ]

    def create(self, validated_data):
        candidate_data = validated_data.pop('candidate')
        
        candidate, created = Candidate.objects.get_or_create(
            email=candidate_data['email'],
            defaults=candidate_data
        )
        
        application = Application.objects.create(candidate=candidate, **validated_data)
        return application