from rest_framework import serializers
from .models import Project, OverheadCost, OtherProduction
from apps.products.models import Product

class SimpleProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', "paid", "balance"]
        read_only_fields = ["id"]


class ProjectSerializer(serializers.ModelSerializer):
    from apps.customers.serializers import SimpleCustomerSerializer
    
    products = serializers.SerializerMethodField()
    sold_items = serializers.SerializerMethodField()
    expenses = serializers.SerializerMethodField()
    other_productions = serializers.SerializerMethodField()
    calculations = serializers.SerializerMethodField()
    customer_detail = SimpleCustomerSerializer(source="customer", read_only=True) # Modified
    total = serializers.SerializerMethodField()


    class Meta:
        model = Project
        fields = [
            'id', 'name', 'invoice_image','selling_price', 'logistics', 'service_charge', 'status', 'start_date',
            'deadline', 'timeframe', 'date_delivered', 'all_items', 'tasks', 'is_delivered', 'archived', 'customer',
            'customer_detail', 'products', 'sold_items', 'expenses', 'other_productions',  'total', 'note',
            "calculations"
        ]
        read_only_fields = ['id']
        extra_kwargs = {'customer': {'write_only': True}}

    def get_products(self, obj):
        from apps.products.serializers import SimpleProductSerializer
        products_data = SimpleProductSerializer(obj.product_set.all(), many=True).data
        total_raw_material_cost = self.get_total_raw_material_cost(obj)
        total_artisan_cost = self.get_total_artisan_cost(obj)
        total_production_cost = round(total_artisan_cost + total_raw_material_cost)
        total_overhead_cost = self.get_total_overhead_cost(obj)
        total_grand_total = round(total_production_cost + total_overhead_cost)
        total_selling_price = obj.product_set.aggregate(
            total=Coalesce(Sum(F("selling_price") * F("quantity")), Decimal(0))
        )["total"]
        total_profit = round(total_selling_price - total_grand_total)

        return {
            "progress": getattr(obj, "computed_progress", 0),
            "total_product_selling_price": round(total_selling_price),
            "total_production_cost": total_production_cost,
            "total_artisan_cost": total_artisan_cost,
            "total_overhead_cost": total_overhead_cost,
            "total_raw_material_cost": total_raw_material_cost,
            "total_grand_total": total_grand_total,
            "total_profit": total_profit,
            "products": products_data
        }

    def get_sold_items(self, obj):
        from apps.shop.serializers import SimpleSoldSerializer
        sold_items = SimpleSoldSerializer(obj.sold_set.all(), many=True).data
        return {
            "total_cost_price_sold_items": self.get_total_cost_price_sold_items(obj),
            "total_selling_price_sold_items": self.get_total_selling_price_sold_items(obj),
            "sold_items": sold_items
        }

    def get_expenses(self, obj):
        from apps.expensis.serializers import SimpleExpenseSerializer
        expenses = SimpleExpenseSerializer(obj.expense_set.all(), many=True).data
        return {
            "total_expenses": self.get_total_expensis(obj),
            "expenses": expenses
        }

    def get_other_productions(self, obj):
        other_productions = SimpleOtherProductionSerializer(obj.otherproduction_set.all(), many=True).data
        return {
            "total_cost": self.get_total_other_productions_cost(obj),
            "total_budget": self.get_total_other_productions_budget(obj),
            "other_productions": other_productions
        }

    def get_calculations(self, obj):
        return {
            "total_raw_material_cost": self.get_total_raw_material_cost(obj),
            "total_artisan_cost": self.get_total_artisan_cost(obj),
            "total_overhead_cost": self.get_total_overhead_cost(obj),
            "total_products_cost": self.get_total_products_cost(obj),
            "total_product_selling_price": self.get_total_product_selling_price(obj),
            "product_profit": self.get_product_profit(obj),
            "total_cost_price_sold_items": self.get_total_cost_price_sold_items(obj),
            "total_selling_price_sold_items": self.get_total_selling_price_sold_items(obj),
            "shop_items_profit": self.get_shop_items_profit(obj),
            "money_left_for_expensis": self.get_money_left_for_expensis(obj),
            "money_left_for_expensis_with_logistics_and_service_charge": self.get_money_left_for_expensis_with_logistics_and_service_charge(obj),
            "total_other_productions_budget": self.get_total_other_productions_budget(obj),
            "total_other_productions_cost": self.get_total_other_productions_cost(obj),
            "total_expensis": self.get_total_expensis(obj),
            "total_money_spent": self.get_total_money_spent(obj),
            "total_paid": self.get_total_paid(obj),
            "final_profit": self.get_final_profit(obj),
        }

    def get_total_raw_material_cost(self, obj):
        from store.models import Removed
        raw_materials = Removed.objects.filter(product__in=obj.product_set.all()).annotate(total_cost=ExpressionWrapper(F("quantity") * F("material__price"), output_field=DecimalField(max_digits=10, decimal_places=2))).aggregate(total=Coalesce(Sum("total_cost"), Decimal(0)))
        return round(raw_materials['total'])

    # products

    def get_total_artisan_cost(self, obj):
        contractor_cost = ProductContractor.objects.filter(product__in=obj.product_set.all()).aggregate(total=Coalesce(Sum("cost"), Decimal(0)))["total"]
        return round(contractor_cost)

    def get_total_overhead_cost(self, obj):
        overhead_cost = obj.product_set.aggregate(total=Coalesce(Sum(F("overhead_cost") * F("overhead_cost_base_at_creation")), Decimal(0)))["total"]
        return round(overhead_cost)

    def get_total_products_cost(self, obj):
        total = self.get_total_raw_material_cost(obj) + self.get_total_artisan_cost(obj) + self.get_total_overhead_cost(obj)
        return round(total)

    def get_total_product_selling_price(self, obj):
        total_selling = obj.product_set.aggregate(total=Coalesce(Sum(F("selling_price") * F("quantity")), Decimal(0)))["total"]
        return round(total_selling)

    def get_product_profit(self, obj):
        total_profit = self.get_total_product_selling_price(obj) - self.get_total_products_cost(obj)
        return round(total_profit)

    # shop_items
    def get_total_cost_price_sold_items(self, obj):
        total_cost = obj.sold_set.aggregate(total=Coalesce(Sum(F("quantity") * F("cost_price")), Decimal(0)))["total"]
        return round(total_cost)

    def get_total_selling_price_sold_items(self, obj):
        total_selling = obj.sold_set.aggregate(total=Coalesce(Sum(F("quantity") * F("selling_price")), Decimal(0)))["total"]
        return round(total_selling)

    def get_shop_items_profit(self, obj):
        total_profit = self.get_total_selling_price_sold_items(obj) - self.get_total_cost_price_sold_items(obj)
        return round(total_profit)

    def get_money_left_for_expensis(self, obj):
        return round((obj.selling_price or Decimal(0)) - (self.get_total_selling_price_sold_items(obj) + self.get_total_product_selling_price(obj)))

    def get_money_left_for_expensis_with_logistics_and_service_charge(self, obj):
        return round(self.get_total_paid(obj) - (self.get_total_selling_price_sold_items(obj) + self.get_total_product_selling_price(obj)))

    # expensis
    def get_total_expensis(self, obj):
        total_expenses = obj.expense_set.aggregate(total=Coalesce(Sum("amount"), Decimal(0)))["total"]
        return round(total_expenses)

    def get_total_other_productions_cost(self, obj):
        total_cost = obj.otherproduction_set.aggregate(total=Coalesce(Sum("cost"), Decimal(0)))["total"]
        return round(total_cost)

    def get_total_other_productions_budget(self, obj):
        total_budget = obj.otherproduction_set.aggregate(total=Coalesce(Sum("budget"), Decimal(0)))["total"]
        return round(total_budget)

    # totals
    def get_total_money_spent(self, obj):
        total = self.get_total_products_cost(obj) + self.get_total_cost_price_sold_items(obj) + self.get_total_other_productions_cost(obj) + self.get_total_expensis(obj)
        return round(total)

    def get_total_paid(self, obj):
        return round(
            (obj.selling_price or Decimal(0)) + (obj.logistics or Decimal(0)) + (obj.service_charge or Decimal(0)))

    def get_total(self, obj):
        return round((obj.selling_price or Decimal(0)) + (obj.logistics or Decimal(0)) + (obj.service_charge or Decimal(0)))

    def get_final_profit(self, obj):
        return self.get_total_paid(obj) - self.get_total_money_spent(obj)


class OverheadCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverheadCost
        fields = ['overhead_cost_base']


class SimpleOtherProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherProduction
        fields = ['id', 'name', 'budget', 'cost']


class OthersSimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']


class OtherProductionSerializer(serializers.ModelSerializer):
    project_link = OthersSimpleProductSerializer(source="project", read_only=True)

    class Meta:
        model = OtherProduction
        fields = ['id', 'name', 'budget', 'project_link', 'cost']
        read_only_fields = ['id']