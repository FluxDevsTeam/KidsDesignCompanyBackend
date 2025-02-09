from rest_framework import serializers


class RawMaterialDashboardSerializer(serializers.Serializer):
    total_raw_materials = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    removed_cost_today = serializers.DecimalField(max_digits=10, decimal_places=2)
    removed_cost_week = serializers.DecimalField(max_digits=10, decimal_places=2)
    removed_cost_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    removed_amount_year = serializers.DecimalField(max_digits=10, decimal_places=2)
    added_amount_year = serializers.DecimalField(max_digits=10, decimal_places=2)
    added_amount_monthly = serializers.ListField()
    removed_amount_monthly = serializers.ListField()


class InventoryDashboardSerializer(serializers.Serializer):
    total_shop_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cost_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit_potential = serializers.DecimalField(max_digits=10, decimal_places=2)
    yearly_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    yearly_added_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_sold_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_added_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_profit = serializers.ListField()
    monthly_added_value = serializers.ListField()
    amount_sold_monthly = serializers.ListField()


class ProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.DateField()


class ContractorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    total_pay = serializers.DecimalField(max_digits=10, decimal_places=2)
    last_month_pay = serializers.DecimalField(max_digits=10, decimal_places=2)
    last_year_pay = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_payments = serializers.ListField()
    projects = ProjectSerializer(many=True)


class SalaryWorkerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    pay = serializers.DecimalField(max_digits=10, decimal_places=2)
    projects = ProjectSerializer(many=True)


class WorkersDashboardSerializer(serializers.Serializer):
    contractors = ContractorSerializer(many=True)
    salary_workers = SalaryWorkerSerializer(many=True)
    salary_costs = serializers.DecimalField(max_digits=10, decimal_places=2)
    contractors_monthly = serializers.ListField()
    current_month_contractor_payments = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_monthly_cost = serializers.DecimalField(max_digits=10, decimal_places=2)


class FinancialHealthSerializer(serializers.Serializer):
    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    active_assets = serializers.DecimalField(max_digits=10, decimal_places=2)
    deprecated_assets = serializers.DecimalField(max_digits=10, decimal_places=2)


class CategoryBreakdownSerializer(serializers.Serializer):
    category = serializers.CharField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class ExpenseDashboardSerializer(serializers.Serializer):
    financial_health = FinancialHealthSerializer()
    category_breakdown = CategoryBreakdownSerializer(many=True)
    monthly_trend = serializers.ListField()
    top_categories = serializers.ListField()
    asset_lifespan = serializers.ListField()


class ProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.DateField()
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    is_owing = serializers.BooleanField()

class ShopItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    item_name = serializers.CharField(source='item.name')
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    date = serializers.DateTimeField()

class CustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    projects = ProjectSerializer(many=True)
    shop_items = ShopItemSerializer(many=True)
    total_spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    is_owing = serializers.BooleanField()

class CustomerDashboardSerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    all_customers = CustomerSerializer(many=True)
    owing_customers = serializers.DictField()
