from django.core.serializers.json import DjangoJSONEncoder
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
        fields = ['id', 'name', 'dimensions', 'inventory_category']
        read_only_fields = ['id']


class SimpleCustomerSerializer(ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name']
        read_only_fields = ['id']


class SimpleProjectSerializer(ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']
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
    class Meta:
        model = Customer
        fields = '__all__'


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


#  ################################################


#  ##############################################
class QuotationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        contractor_ids = data.get("contractor", [])
        contractor_list = []
        salary_worker_ids = data.get("salary_worker", [])
        salary_worker_list = []

        for contractor_id in contractor_ids:
            contractor_obj = get_object_or_404(Contractors, id=contractor_id)
            contractor_list.append({
                "id": contractor_obj.id,
                "name": f"{contractor_obj.first_name} {contractor_obj.last_name}"
            })

        data["contractor"] = contractor_list

        for salary_worker_id in salary_worker_ids:
            salary_worker_obj = get_object_or_404(SalaryWorkers, id=salary_worker_id)
            salary_worker_list.append({
                "id": salary_worker_obj.id,
                "name": f"{salary_worker_obj.first_name} {salary_worker_obj.last_name}"
            })

        data["salary_worker"] = salary_worker_list
        return data

    class Meta:
        model = Quotation
        fields = "__all__"
        read_only_fields = ['id', 'product']


class ProductContractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductContractor
        fields = ["id", "product", "contractor", "cost"]
        read_only_fields = ['id', 'product']


class ProductSalaryWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSalaryWorker
        fields = ["id", "product", "salary_worker", ]
        read_only_fields = ['id', 'product']


class ProductSerializer(ModelSerializer):
    contractors = ProductContractorSerializer(source="productcontractor_set", many=True, read_only=True)
    salary_workers = ProductSalaryWorkerSerializer(source="productsalaryworker_set", many=True, read_only=True)
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.filter(archived=False, is_delivered=False),
                                                 required=False, allow_null=True, write_only=True)
    linked_project = SimpleProjectSerializer(source="project", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "project", "linked_project", "name", "images", "sketch", "dimensions", "colour", "design",
            "production_note", "progress",
            "contractors", "salary_workers", "selling_price", "overhead_cost", "overhead_cost_base_at_creation",
            "total_raw_material_cost", "total_artisan_cost", "quantity", "total_production_cost", "grand_total",
            "grand_total_per_item", "profit", "profit_per_item"
        ]
        read_only_fields = ['overhead_cost_base_at_creation']


class RawMaterialUsedSerializer(ModelSerializer):
    class Meta:
        model = Removed
        fields = '__all__'


class StoreCategorySerializer(ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class RawMaterialSerializer(ModelSerializer):
    store_category = StoreCategorySerializer(source="category", read_only=True)

    class Meta:
        model = RawMaterial
        fields = ["id", "name", "unit", "quantity", "price", "category", "store_category", "description", "image", ]
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


class SimpleExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['name', 'amount']


class SimpleProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'selling_price', 'grand_total', 'profit']


class SimpleSoldSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = Sold
        fields = ['id', 'name', 'quantity', 'cost_price', 'selling_price', 'total_price']


class SimpleOtherProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherProduction
        fields = ['id', 'name', 'cost']


class ProjectSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    sold_items = serializers.SerializerMethodField()
    expenses = serializers.SerializerMethodField()
    total_project_cost = serializers.SerializerMethodField()
    total_project_selling_price = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_money_spent = serializers.SerializerMethodField()
    final_profit = serializers.SerializerMethodField()
    other_productions = serializers.SerializerMethodField()
    customer_detail = SimpleCustomerSerializer(source="customer", read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'invoice_image', 'status', 'start_date', 'deadline', 'timeframe', 'date_delivered',
            'all_items', 'total_project_selling_price', 'is_delivered', 'archived', 'customer', 'customer_detail',
            'products', 'sold_items', 'expenses', 'other_productions', 'selling_price', 'logistics',
            'service_charge', 'total_project_cost', 'total_paid', 'total_money_spent', 'final_profit', 'note'
        ]
        read_only_fields = ['id', 'start_date']
        extra_kwargs = {'customer': {'write_only': True}}

        # """   format    """
        # {
        #     "Task A": {"completed": false},
        #     "Task B": {"completed": true}
        # }

    def get_products(self, obj):
        products = SimpleProductSerializer(obj.product_set.all(), many=True).data
        return {
            "progress": getattr(obj, "computed_progress", 0),
            "total_project_selling_price": self.get_total_project_selling_price(obj),
            "total_production_cost": self.get_total_production_cost(obj),
            "total_artisan_cost": self.get_total_artisan_cost(obj),
            "total_overhead_cost": self.get_total_overhead_cost(obj),
            "total_raw_material_cost": self.get_total_raw_material_cost(obj),
            "total_grand_total": self.get_total_grand_total(obj),
            "total_profit": self.get_total_profit(obj),
            "products": products
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
            "total_expenses": self.get_total_expenses(obj),
            "expenses": expenses
        }

    def get_other_productions(self, obj):
        other_productions = SimpleOtherProductionSerializer(obj.otherproduction_set.all(), many=True).data
        return {
            "total_cost": self.get_total_other_productions_cost(obj),
            "total_budget": self.get_total_other_productions_budget(obj),
            "other_productions": other_productions
        }

    def get_total_other_productions_cost(self, obj):
        return round(sum(getattr(op, "cost", 0) for op in obj.otherproduction_set.all()))

    def get_total_other_productions_budget(self, obj):
        return round(sum(getattr(op, "budget", 0) for op in obj.otherproduction_set.all()))

    def get_total_grand_total(self, obj):
        return round(sum(getattr(product, "grand_total", 0) for product in obj.product_set.all()))

    def get_total_project_selling_price(self, obj):
        return round(sum(getattr(product, "selling_price", 0) for product in obj.product_set.all()))

    def get_total_production_cost(self, obj):
        return round(sum(getattr(product, "total_production_cost", 0) for product in obj.product_set.all()))

    def get_total_artisan_cost(self, obj):
        return round(sum(getattr(product, "total_artisan_cost", 0) for product in obj.product_set.all()))

    def get_total_overhead_cost(self, obj):
        return round(sum(
            getattr(product, "overhead_cost", 0) * getattr(product, "overhead_cost_base_at_creation", 0)
            for product in obj.product_set.all()
        ))

    def get_total_raw_material_cost(self, obj):
        return round(sum(getattr(product, "total_raw_material_cost", 0) for product in obj.product_set.all()))

    def get_total_profit(self, obj):
        product_profit = sum(getattr(product, "profit", 0) for product in obj.product_set.all())
        sold_profit = sum(
            getattr(sold, "quantity", 0) * (
                getattr(getattr(sold, "item", None), "selling_price", 0) -
                getattr(getattr(sold, "item", None), "cost_price", 0)
            )
            for sold in obj.sold_set.all()
        )
        return round(product_profit + sold_profit)

    def get_total_expenses(self, obj):
        return round(sum(getattr(expense, "amount", 0) for expense in obj.expense_set.all()))

    def get_total_cost_price_sold_items(self, obj):
        return round(sum(
            getattr(sold, "quantity", 0) * getattr(getattr(sold, "item", None), "cost_price", 0)
            for sold in obj.sold_set.all()
        ))

    def get_total_selling_price_sold_items(self, obj):
        return round(sum(
            getattr(sold, "quantity", 0) * getattr(getattr(sold, "item", None), "selling_price", 0)
            for sold in obj.sold_set.all()
        ))

    def get_total_project_cost(self, obj):
        return self.get_total_grand_total(obj) + self.get_total_cost_price_sold_items(obj)

    def get_total_paid(self, obj):
        return round(
            getattr(obj, "selling_price", 0) +
            getattr(obj, "logistics", 0) +
            getattr(obj, "service_charge", 0)
        )

    def get_total_money_spent(self, obj):
        return (
            self.get_total_expenses(obj) +
            self.get_total_project_cost(obj) +
            self.get_total_other_productions_cost(obj)
        )

    def get_final_profit(self, obj):
        return self.get_total_paid(obj) - self.get_total_money_spent(obj)


#  #########################################
#  ###################################


class SimpleRawMaterialSerializer(ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = ['id', 'name']


class RemovedSerializer(ModelSerializer):
    product_its_used = SimpleProductSerializer(source="product", read_only=True)
    raw_material = SimpleRawMaterialSerializer(source="material", read_only=True)

    class Meta:
        model = Removed
        fields = ["id", "material", "raw_material", "quantity", "price", "product", "product_its_used", "date"]
        read_only_fields = ["id", "date"]
        extra_kwargs = {'material': {'write_only': True}, 'product': {'write_only': True}}


class SimpleContractorsSerializer(ModelSerializer):
    class Meta:
        model = Contractors
        fields = ['id', 'first_name', 'last_name']


class SimpleSalaryWorkersSerializer(ModelSerializer):
    class Meta:
        model = SalaryWorkers
        fields = ['id', 'first_name', 'last_name']


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
        fields = ['name', 'value', 'expected_lifespan', 'is_still_available', 'get_total_value']


class AddRawMaterialsSerializer(ModelSerializer):
    material = SimpleRawMaterialSerializer(source="item", read_only=True)

    class Meta:
        model = AddRawMaterials
        fields = ["item", "material", "quantity", "date"]
        extra_kwargs = {'item': {'write_only': True}}
