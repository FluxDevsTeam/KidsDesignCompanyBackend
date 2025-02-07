from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from shop.models import InventoryItem, Sold, InventoryCategory, AddStock
from customers.models import Customer
from expensis.models import Expense, ExpenseCategory
from products.models import Quotation, Product, ProductContractor, ProductSalaryWorker
from project.models import Project
from store.models import RawMaterial, Removed, StoreCategory
from workers.models import Contractors, SalaryWorkers, ContractorRecord, SalaryWorkersRecord
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.shortcuts import get_object_or_404
from decimal import Decimal

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
                  'item_sold',
                  'cost_price', 'selling_price', 'total_price', 'profit']
        read_only_fields = ['id', 'updated_on', 'project']
        extra_kwargs = {'customer': {'write_only': True}, 'item': {'write_only': True}}


class AddSockSerializer(ModelSerializer):
    inventory_item = InventoryItemSerializer(source="category", read_only=True)

    class Meta:
        model = AddStock
        fields = ["item", "inventory_item", "quantity", "date"]
        extra_kwargs = {'item': {'write_only': True}}


class CustomerSerializer(ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class ExpenseCategorySerializer(ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class ExpenseSerializer(ModelSerializer):
    expense_category = ExpenseCategorySerializer(source="category", read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'name', 'category', 'expense_category', 'description', 'amount', 'quantity', 'date']
        read_only_fields = ['id', 'date']
        extra_kwargs = {'category': {'write_only': True}}


# not done yet #############################################################################
class ContractorsSerializer(ModelSerializer):
    class Meta:
        model = Contractors
        fields = '__all__'


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
        fields = ["id", "product", "salary_worker", "cost"]
        read_only_fields = ['id', 'product']


class ProductSerializer(ModelSerializer):
    contractors = ProductContractorSerializer(source="productcontractor_set", many=True, read_only=True)
    salary_workers = ProductSalaryWorkerSerializer(source="productsalaryworker_set", many=True, read_only=True)

    total_raw_material_cost = serializers.SerializerMethodField()
    total_artisan_cost = serializers.SerializerMethodField()
    total_production_cost = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "quantity", "images", "dimensions", "colour", "design",
            "contractors", "salary_workers", "selling_price", "overhead_cost",
            "total_raw_material_cost", "total_artisan_cost",
            "total_production_cost", "grand_total", "profit"
        ]

    def get_total_raw_material_cost(self, obj):
        raw_materials = Removed.objects.filter(product=obj).annotate(
            total_cost=ExpressionWrapper(F("quantity") * F("material__price"), output_field=DecimalField())
        ).aggregate(total=Sum("total_cost"))["total"]

        return raw_materials or Decimal(0)

    def get_total_artisan_cost(self, obj):
        contractor_cost = ProductContractor.objects.filter(product=obj).aggregate(total=Sum("cost"))["total"] or Decimal(0)
        salary_worker_cost = ProductSalaryWorker.objects.filter(product=obj).aggregate(total=Sum("cost"))["total"] or Decimal(0)
        return contractor_cost + salary_worker_cost

    def get_total_production_cost(self, obj):
        return self.get_total_artisan_cost(obj) + self.get_total_raw_material_cost(obj)

    def get_grand_total(self, obj):
        return obj.overhead_cost + self.get_total_production_cost(obj)

    def get_profit(self, obj):
        return (obj.selling_price * obj.quantity) - self.get_grand_total(obj)


class RawMaterialUsedSerializer(ModelSerializer):
    class Meta:
        model = Removed
        fields = '__all__'


# ##################################################
class StoreCategorySerializer(ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class RawMaterialSerializer(ModelSerializer):
    store_category = StoreCategorySerializer(source="category", read_only=True)

    class Meta:
        model = RawMaterial
        fields = ["id", "name", "unit", "quantity", "price", "category", "store_category", "description", "image",
                  "cost_per_unit"]
        read_only_fields = ["id"]


class ProjectSerializer(ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ["id", "start_date"]


class SimpleProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']


class SimpleRawMaterialSerializer(ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = ['id', 'name']


class RemovedSerializer(ModelSerializer):
    product_its_used = SimpleProductSerializer(source="product", read_only=True)
    raw_material = SimpleRawMaterialSerializer(source="material", read_only=True)

    class Meta:
        model = Removed
        fields = ["id", "material", "raw_material", "quantity", "product", "product_its_used", "date"]
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


class SalaryWorkersRecordSerializer(ModelSerializer):
    worker = SimpleContractorsSerializer(source="salary_worker", read_only=True)

    class Meta:
        model = SalaryWorkersRecord
        fields = ['id', 'report', 'date', 'worker']
        read_only_fields = ['id', 'date']

