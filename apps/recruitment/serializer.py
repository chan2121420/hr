from rest_framework import serializers
from .models import JobPosting, Candidate, Application, Interview, Onboarding

class JobPostingSerializer(serializers.ModelSerializer):
    position_title = serializers.CharField(source='position.title', read_only=True)
    department_name = serializers.CharField(source='position.department.name', read_only=True)
    applications_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPosting
        fields = '__all__'
    
    def get_applications_count(self, obj):
        return obj.applications.count()

class CandidateSerializer(serializers.ModelSerializer):
    applications_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = '__all__'
    
    def get_applications_count(self, obj):
        return obj.applications.count()

class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.first_name', read_only=True)
    job_title = serializers.CharField(source='job_posting.title', read_only=True)
    screened_by_name = serializers.CharField(source='screened_by.get_full_name', read_only=True)
    
    class Meta:
        model = Application
        fields = '__all__'

class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    job_title = serializers.CharField(source='application.job_posting.title', read_only=True)
    
    class Meta:
        model = Interview
        fields = '__all__'
    
    def get_candidate_name(self, obj):
        return f"{obj.application.candidate.first_name} {obj.application.candidate.last_name}"
