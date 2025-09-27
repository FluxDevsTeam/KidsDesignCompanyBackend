from rest_framework import serializers
from .models import Income, IncomeCategory, Balance, BalanceSwitchLog
from apps.customers.serializers import SimpleCustomerSerializer

class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Balance
        fields = ["cash", "bank"]


class IncomeCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = IncomeCategory
        fields = ["id", "name"]
        read_only_fields = ["id"]


class IncomeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Income
        fields = ["name", "category", "amount", "cash", "date"]
        read_only_fields = ["id"]


class IncomeSerializerView(serializers.ModelSerializer):
    category = IncomeCategorySerializer()

    class Meta:
        model = Income
        fields = ["id", "name", "category", "amount", "cash", "date"]
        read_only_fields = ["id"]


class BalanceSwitchLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceSwitchLog
        fields = ['id', 'from_method', 'to_method', 'amount', 'switch_date']
        read_only_fields = ['id']

    def validate(self, attrs):
        from_method = attrs.get('from_method')
        to_method = attrs.get('to_method')
        amount = attrs.get('amount')
        switch_date = attrs.get('switch_date', date.today())
        balance, _ = Balance.objects.get_or_create(id=1)

        if from_method == to_method:
            raise serializers.ValidationError("Source and destination methods must be different")
        if amount <= 0:
            raise serializers.ValidationError("Amount must be positive")
        if switch_date > date.today():
            raise serializers.ValidationError("Switch date cannot be in the future")
        if self.instance:
            temp_balance = {
                'cash': balance.cash,
                'bank': balance.bank,
                'debt': balance.debt
            }
            if self.instance.from_method == 'CASH':
                temp_balance['cash'] += self.instance.amount
            elif self.instance.from_method == 'BANK':
                temp_balance['bank'] += self.instance.amount
            elif self.instance.from_method == 'DEBT':
                temp_balance['debt'] += self.instance.amount
            if self.instance.to_method == 'CASH':
                temp_balance['cash'] -= self.instance.amount
            elif self.instance.to_method == 'BANK':
                temp_balance['bank'] -= self.instance.amount
            elif self.instance.to_method == 'DEBT':
                temp_balance['debt'] -= self.instance.amount
            if from_method == 'CASH' and temp_balance['cash'] < amount:
                raise serializers.ValidationError(
                    f"Insufficient cash balance ({temp_balance['cash']}) for transfer of {amount}")
            if from_method == 'BANK' and temp_balance['bank'] < amount:
                raise serializers.ValidationError(
                    f"Insufficient bank balance ({temp_balance['bank']}) for transfer of {amount}")
            if from_method == 'DEBT' and temp_balance['debt'] < amount:
                raise serializers.ValidationError(
                    f"Insufficient debt balance ({temp_balance['debt']}) for transfer of {amount}")
        else:
            if from_method == 'CASH' and balance.cash < amount:
                raise serializers.ValidationError(
                    f"Insufficient cash balance ({balance.cash}) for transfer of {amount}")
            if from_method == 'BANK' and balance.bank < amount:
                raise serializers.ValidationError(
                    f"Insufficient bank balance ({balance.bank}) for transfer of {amount}")
            if from_method == 'DEBT' and balance.debt < amount:
                raise serializers.ValidationError(
                    f"Insufficient debt balance ({balance.debt}) for transfer of {amount}")
        return attrs