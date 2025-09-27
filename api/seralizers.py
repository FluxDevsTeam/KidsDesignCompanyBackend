from rest_framework import serializers

from apps.expensis.models import Expense
from apps.project.models import OtherProduction, OverheadCost
from apps.shop.models import Sold
from apps.workers.models import Contractors


class SimpleExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['name', 'amount', 'quantity', 'date']


class SimpleContractorsSerializer(ModelSerializer):
    class Meta:
        model = Contractors
        fields = ['id', 'first_name', 'last_name']


class SimpleSoldSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = Sold
        fields = ['id', 'name', 'quantity', 'cost_price', 'selling_price', 'total_price']


class SimpleOtherProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherProduction
        fields = ['id', 'name', 'budget', 'cost']


class OverheadCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverheadCost
        fields = ['overhead_cost_base']
