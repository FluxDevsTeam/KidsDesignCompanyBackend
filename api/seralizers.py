from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.functions import Coalesce
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, ListSerializer
from rest_framework import serializers
from shop.models import InventoryItem, Sold, InventoryCategory, AddStock
from customers.models import Customer
from expensis.models import Expense, ExpenseCategory, Assets
from products.models import Quotation, Product, ProductContractor, ProductSalaryWorker
from project.models import Project, OverheadCost, OtherProduction
from store.models import RawMaterial, Removed, StoreCategory, AddRawMaterials
from workers.models import Contractors, SalaryWorkers, ContractorRecord, SalaryWorkersRecord, Paid
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
import json

from django.shortcuts import get_object_or_404
from decimal import Decimal


class SimpleExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['name', 'amount']


class SimpleContractorsSerializer(ModelSerializer):
    class Meta:
        model = Contractors
        fields = ['id', 'first_name', 'last_name']


class SimpleProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'selling_price', 'progress']


class SimpleSoldSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = Sold
        fields = ['id', 'name', 'quantity', 'cost_price', 'selling_price', 'total_price']


class SimpleOtherProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherProduction
        fields = ['id', 'name', 'cost']


class OverheadCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverheadCost
        fields = ['overhead_cost_base']


class InventoryCategorySerializer(ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class InventoryItemSerializer(ModelSerializer):
    inventory_category = InventoryCategorySerializer(source="category", read_only=True)

    class Meta:
        model = InventoryItem
        fields = ['id', 'name', 'category', 'inventory_category', 'description', 'image', 'stock', 'cost_price',
                  'selling_price', 'dimensions', "archived", "profit_per_item", "total_price"]
        read_only_fields = ['id']
        extra_kwargs = {'category': {'write_only': True}}


class SimpleInventoryItemSerializer(ModelSerializer):
    inventory_category = InventoryCategorySerializer(source="category", read_only=True)

    class Meta:
        model = InventoryItem
        fields = ['id', 'name', 'dimensions', 'inventory_category', 'image']
        read_only_fields = ['id']


class SimpleSalaryWorkersSerializer(ModelSerializer):
    class Meta:
        model = SalaryWorkers
        fields = ['id', 'first_name', 'last_name']


class SimpleCustomerSerializer(ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name']
        read_only_fields = ['id']


class SimpleProjectSerializer(ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', "paid", "balance"]
        read_only_fields = ["id"]


class SoldSerializer(ModelSerializer):
    item_sold = SimpleInventoryItemSerializer(source="item", read_only=True)
    sold_to = SimpleCustomerSerializer(source="customer", read_only=True)
    linked_project = SimpleProjectSerializer(source="project", read_only=True)

    class Meta:
        model = Sold
        fields = ['id', 'quantity', 'date', 'updated_on', 'customer', 'sold_to', 'project', 'linked_project', 'item',
                  'name', 'item_sold', 'logistics', 'cost_price', 'selling_price', 'total_price', 'profit']
        read_only_fields = ['id', 'updated_on', 'selling_price', 'cost_price', 'name']
        extra_kwargs = {'customer': {'write_only': True}, 'item': {'write_only': True}, 'project': {'write_only': True}}


class AddSockSerializer(ModelSerializer):
    inventory_item = SimpleInventoryItemSerializer(source="item", read_only=True)

    class Meta:
        model = AddStock
        fields = ["id", "item", "inventory_item", "name", "quantity", "cost_price", "date"]
        extra_kwargs = {'item': {'write_only': True}}
        read_only_fields = ['id', 'name', 'cost_price']


class CustomerSerializer(ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    shop_item = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone_number", "address", "project", "shop_item", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_project(self, obj):
        project = obj.project_set.first()
        return SimpleProjectSerializer(project).data if project else None

    def get_shop_item(self, obj):
        shop_item = obj.sold_set.first()
        return SimpleSoldSerializer(shop_item).data if shop_item else None


class CustomerDetailSerializer(ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    shop_item = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone_number", "address", "project", "shop_item", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_project(self, obj):
        project = obj.project_set.all()
        return SimpleProjectSerializer(project, many=True).data if project else None

    def get_shop_item(self, obj):
        shop_item = obj.sold_set.all()
        return SimpleSoldSerializer(shop_item, many=True).data if shop_item else None


class ExpenseCategorySerializer(ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


# not done yet #############################################################################
class ContractorsSerializer(ModelSerializer):
    class Meta:
        model = Contractors
        fields = '__all__'


class PaidSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paid
        fields = '__all__'

    def validate(self, attrs):
        if not attrs.get("salary") and not attrs.get("contract"):
            raise serializers.ValidationError({"error": "Either salary or contract is required."})

        if attrs.get("salary") and attrs.get("contract"):
            raise serializers.ValidationError({"error": "Only one of salary or contract is allowed."})

        return attrs


class SalaryWorkersSerializer(ModelSerializer):
    class Meta:
        model = SalaryWorkers
        fields = '__all__'


class QuotationSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = "__all__"
        read_only_fields = ['id', 'product']

    def get_product_name(self, obj):
        return obj.product.name  # Fetch the product name

    def get_project_name(self, obj):
        return obj.product.project.name if obj.product.project else None  # Fetch the project name

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Process contractor list
        contractor_ids = data.get("contractor", [])
        contractor_list = []
        for contractor_id in contractor_ids:
            contractor_obj = get_object_or_404(Contractors, id=contractor_id)
            contractor_list.append({
                "id": contractor_obj.id,
                "name": f"{contractor_obj.first_name} {contractor_obj.last_name}"
            })
        data["contractor"] = contractor_list

        # Process salary worker list
        salary_worker_ids = data.get("salary_worker", [])
        salary_worker_list = []
        for salary_worker_id in salary_worker_ids:
            salary_worker_obj = get_object_or_404(SalaryWorkers, id=salary_worker_id)
            salary_worker_list.append({
                "id": salary_worker_obj.id,
                "name": f"{salary_worker_obj.first_name} {salary_worker_obj.last_name}"
            })
        data["salary_worker"] = salary_worker_list

        return data


class ProductContractorSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer(read_only=True)
    linked_contractor = SimpleContractorsSerializer(source="contractor", read_only=True)

    class Meta:
        model = ProductContractor
        fields = ["id", "product", "linked_contractor", "cost"]
        read_only_fields = ['id', 'product']
        extra_kwargs = {'contractor': {'write_only': True}, }


class ProductSalaryWorkerSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer(read_only=True)
    linked_salary_worker = SimpleSalaryWorkersSerializer(source="salary_worker", read_only=True)

    class Meta:
        model = ProductSalaryWorker
        fields = ["id", "product", "salary_worker", "linked_salary_worker", ]
        read_only_fields = ['id', 'product']
        extra_kwargs = {'salary_worker': {'write_only': True}, }


class ProductSerializer(serializers.ModelSerializer):
    contractors = ProductContractorSerializer(source="productcontractor_set", many=True, read_only=True)
    salary_workers = ProductSalaryWorkerSerializer(source="productsalaryworker_set", many=True, read_only=True)
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.filter(archived=False, is_delivered=False),required=False,allow_null=True,write_only=True)
    linked_project = SimpleProjectSerializer(source="project", read_only=True)

    calculations = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "project", "linked_project", "name", "images", "sketch", "dimensions", "colour", "design",
            "production_note", "progress", "contractors", "salary_workers", "selling_price", "overhead_cost",
            "overhead_cost_base_at_creation", "calculations"]
        read_only_fields = ['overhead_cost_base_at_creation']

    def get_calculations(self, obj):
        return {
            "total_raw_material_cost": self.get_total_raw_material_cost(obj),
            "total_artisan_cost": self.get_total_artisan_cost(obj),
            "total_overhead_cost": self.get_total_overhead_cost(obj),
            "total_production_cost": self.get_total_production_cost(obj),
            "profit": self.get_profit(obj),
            "quantity": obj.quantity,
            "total_per_item": self.get_total_per_item(obj),
            "profit_per_item": self.get_total_raw_material_cost(obj),
        }

    def get_total_raw_material_cost(self, obj):
        raw_materials = obj.removed_set.filter(product=obj).annotate(total_cost=ExpressionWrapper(F("quantity") * F("material__price"), output_field=DecimalField(max_digits=10, decimal_places=2))).aggregate(total=Coalesce(Sum("total_cost"), Decimal(0)))
        return raw_materials['total']

    def get_total_artisan_cost(self, obj):
        contractor_cost = obj.productcontractor_set.aggregate(total=Sum("cost"))["total"] or 0
        return round(contractor_cost)

    def get_total_overhead_cost(self, obj):
        calculated_overhead = obj.overhead_cost * obj.overhead_cost_base_at_creation
        return calculated_overhead

    def get_total_production_cost(self, obj):
        total = self.get_total_artisan_cost(obj) + self.get_total_overhead_cost(obj) + self.get_total_raw_material_cost(obj)
        return round(total)

    def get_total_per_item(self, obj):
        unit_total = self.get_total_production_cost(obj) / obj.quantity
        return round(unit_total)

    def get_profit(self, obj):
        return round((obj.selling_price * obj.quantity) - self.get_total_production_cost(obj))

    def get_profit_per_item(self, obj):
        return round(self.get_profit(obj) / obj.quantity)


class RawMaterialUsedSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    material__name = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)


class StoreCategorySerializer(ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class RawMaterialSerializer(ModelSerializer):
    store_category = StoreCategorySerializer(source="category", read_only=True)

    class Meta:
        model = RawMaterial
        fields = ["id", "name", "unit", "quantity", "price", "category", "store_category", "archived", "description", "image", ]
        read_only_fields = ["id"]


class SimpleRawMaterialSerializer(ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = ["id", "name", "unit"]
        read_only_fields = ["id"]


class OthersSimpleProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']


class OtherProductionSerializer(ModelSerializer):
    project_link = OthersSimpleProductSerializer(source="project", read_only=True)

    class Meta:
        model = OtherProduction
        fields = ['id', 'name', 'budget', 'project_link', 'cost']
        read_only_fields = ['id']


class ProjectSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    sold_items = serializers.SerializerMethodField()
    expenses = serializers.SerializerMethodField()
    other_productions = serializers.SerializerMethodField()
    calculations = serializers.SerializerMethodField()
    customer_detail = SimpleCustomerSerializer(source="customer", read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'invoice_image', 'status', 'start_date', 'deadline', 'timeframe', 'date_delivered',
            'all_items', 'is_delivered', 'archived', 'customer', 'customer_detail',
            'products', 'sold_items', 'expenses', 'other_productions', 'selling_price', 'logistics',
            'service_charge', 'note', "calculations"
        ]
        read_only_fields = ['id', 'start_date']
        extra_kwargs = {'customer': {'write_only': True}}

    def get_products(self, obj):
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
            "total_project_selling_price": round(total_selling_price),
            "total_production_cost": total_production_cost,
            "total_artisan_cost": total_artisan_cost,
            "total_overhead_cost": total_overhead_cost,
            "total_raw_material_cost": total_raw_material_cost,
            "total_grand_total": total_grand_total,
            "total_profit": total_profit,
            "products": products_data
        }

    def get_sold_items(self, obj):
        sold_items = SimpleSoldSerializer(obj.sold_set.all(), many=True).data
        return {
            "total_cost_price_sold_items": self.get_total_cost_price_sold_items(obj),
            "total_selling_price_sold_items": self.get_total_selling_price_sold_items(obj),
            "sold_items": sold_items
        }

    def get_expenses(self, obj):
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

    def get_final_profit(self, obj):
        return self.get_total_paid(obj) - self.get_total_money_spent(obj)


class RemovedSerializer(ModelSerializer):
    product_its_used = SimpleProductSerializer(source="product", read_only=True)
    raw_material = SimpleRawMaterialSerializer(source="material", read_only=True)

    class Meta:
        model = Removed
        fields = ["id", "material", "raw_material", "quantity", "price", "product", "product_its_used", "date"]
        read_only_fields = ["id", "date"]
        extra_kwargs = {'material': {'write_only': True}, 'product': {'write_only': True}}


class ContractorRecordSerializer(ModelSerializer):
    worker = SimpleContractorsSerializer(source="contractor", read_only=True)

    class Meta:
        model = ContractorRecord
        fields = ['id', 'report', 'date', 'worker']
        read_only_fields = ['id', 'date']


class ExpenseSerializer(ModelSerializer):
    expense_category = ExpenseCategorySerializer(source="category", read_only=True)
    linked_project = SimpleProjectSerializer(source="project", read_only=True)
    sold_item = SimpleSoldSerializer(source="shop", read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'name', 'category', 'expense_category', 'description', 'project', 'shop', 'linked_project',
                  'sold_item', 'amount', 'quantity', 'date']
        read_only_fields = ['id', 'date']
        extra_kwargs = {'category': {'write_only': True}, 'project': {'write_only': True}, 'shop': {'write_only': True}}

    def validate(self, attrs):
        project_provided = 'project' in attrs
        shop_provided = 'shop' in attrs

        if self.partial:
            if project_provided and not shop_provided:
                attrs['shop'] = None
            elif shop_provided and not project_provided:
                attrs['project'] = None

        project = attrs.get('project')
        shop = attrs.get('shop')
        if project and shop:
            raise serializers.ValidationError(
                "Expense cannot be associated with both a project and a shop item."
            )

        return attrs


class SalaryWorkersRecordSerializer(ModelSerializer):
    worker = SimpleContractorsSerializer(source="salary_worker", read_only=True)

    class Meta:
        model = SalaryWorkersRecord
        fields = ['id', 'report', 'date', 'worker']
        read_only_fields = ['id', 'date']


class AssetsSerializer(ModelSerializer):
    class Meta:
        model = Assets
        fields = ["id", 'name', 'value', 'expected_lifespan', 'is_still_available', "date_added"]
        read_only_fields = ["id"]


class AddRawMaterialsSerializer(ModelSerializer):
    material = SimpleRawMaterialSerializer(source="item", read_only=True)

    class Meta:
        model = AddRawMaterials
        fields = ["item", "material", "quantity", "cost_price", "date"]
        extra_kwargs = {'item': {'write_only': True}}
