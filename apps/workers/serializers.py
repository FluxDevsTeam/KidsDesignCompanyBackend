from rest_framework import serializers
from .models import Contractors, SalaryWorkers, ContractorRecord, SalaryWorkersRecord, Paid

class SimpleContractorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contractors
        fields = ['id', 'first_name', 'last_name']


class SimpleSalaryWorkersSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryWorkers
        fields = ['id', 'first_name', 'last_name']


class ContractorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contractors
        fields = '__all__'


class SalaryWorkersSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryWorkers
        fields = '__all__'

class ContractorRecordSerializer(serializers.ModelSerializer):
    worker = SimpleContractorsSerializer(source="contractor", read_only=True)

    class Meta:
        model = ContractorRecord
        fields = ['id', 'report', 'date', 'worker']
        read_only_fields = ['id']


class SalaryWorkersRecordSerializer(serializers.ModelSerializer):
    worker = SimpleContractorsSerializer(source="salary_worker", read_only=True)

    class Meta:
        model = SalaryWorkersRecord
        fields = ['id', 'report', 'date', 'worker']
        read_only_fields = ['id']



class PaidSerializer(serializers.ModelSerializer):
    contractor_detail = ContractorsSerializer(source="contract", read_only=True)
    salary_detail = SalaryWorkersSerializer(source="salary", read_only=True)

    class Meta:
        model = Paid
        fields = ["id", "amount", "salary", "contract", "date", "contractor_detail", "salary_detail"]
        read_only_fields = ['id']
        extra_kwargs = {'salary': {'write_only': True}, 'contract': {'write_only': True}}

    def validate(self, attrs):
        if not attrs.get("salary") and not attrs.get("contract"):
            raise serializers.ValidationError({"error": "Either salary or contract is required."})

        if attrs.get("salary") and attrs.get("contract"):
            raise serializers.ValidationError({"error": "Only one of salary or contract is allowed."})

        return attrs
