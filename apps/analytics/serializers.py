from rest_framework import serializers

class KeyValueSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.IntegerField()

class PayrollSummarySerializer(serializers.Serializer):
    total_payroll = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_deductions = serializers.DecimalField(max_digits=15, decimal_places=2)
    employee_count = serializers.IntegerField()

class LeaveBreakdownSerializer(serializers.Serializer):
    leave_type = serializers.CharField()
    days_taken = serializers.IntegerField()

class PerformanceDistributionSerializer(serializers.Serializer):
    rating = serializers.IntegerField()
    count = serializers.IntegerField()