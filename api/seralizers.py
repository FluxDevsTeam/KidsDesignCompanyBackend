from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from shop.models import InventoryItem, Sold, InventoryCategory
from customers.models import Customer
from expensis.models import Expense, ExpenseCategory
from products.models import Quotation, Product, ProductContractor, ProductSalaryWorker
from project.models import Project
from store.models import RawMaterial, Removed, StoreCategory
from workers.models import Contractors, SalaryWorkers
from django.db.models import Sum
from datetime import datetime
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404


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
                  'selling_price', 'dimensions']
        read_only_fields = ['id']
        extra_kwargs = {'category': {'write_only': True}}


class SoldSerializer(ModelSerializer):
    class Meta:
        model = Sold
        fields = ['id', 'quantity', 'date', 'updated_on', 'customer', 'item', 'total_price', 'profit']
        read_only_fields = ['id', 'updated_on']


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

        data["contractor"] = contractor_list
        data["salary_worker"] = salary_worker_list
        return data

    class Meta:
        model = Quotation
        fields = "__all__"
        read_only_fields = ['id', 'product']


class ProductContractorSerializer(serializers.ModelSerializer):
    # contractor = ContractorsSerializer()

    class Meta:
        model = ProductContractor
        fields = ["id", "product", "contractor", "cost"]
        read_only_fields = ['id', 'product']


class ProductSalaryWorkerSerializer(serializers.ModelSerializer):
    # salary_worker = SalaryWorkersSerializer()

    class Meta:
        model = ProductSalaryWorker
        fields = ["id", "product", "salary_worker", "cost"]
        read_only_fields = ['id', 'product']


class ProductSerializer(serializers.ModelSerializer):
    contractors = ProductContractorSerializer(source="productcontractor_set", many=True, read_only=True)
    salary_workers = ProductSalaryWorkerSerializer(source="productsalaryworker_set", many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "quantity", "images", "dimensions", "colour", "design",
            "contractors", "salary_workers", "selling_price", "overhead_cost", "total_production_cost", "profit"
        ]


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
        fields = ["id", "name", "unit", "quantity", "price", "category", "store_category", "description", "image", "cost_per_unit"]
        read_only_fields = ["id"]


class ProjectSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class RemovedSerializer(ModelSerializer):
    class Meta:
        model = Removed
        fields = '__all__'