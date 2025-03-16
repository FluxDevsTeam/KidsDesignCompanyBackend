from rest_framework.serializers import ModelSerializer, ListSerializer
from customers.models import Customer


class SimpleCustomerSerializer(ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name']
        read_only_fields = ['id']
