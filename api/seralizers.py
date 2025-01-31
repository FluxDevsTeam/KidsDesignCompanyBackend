from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from shop.models import InventoryItem, Sold, InventoryCategory
from customers.models import Customer
from expensis.models import Expense, ExpenseCategory
from products.models import Quotation, RawMaterialUsed, Product, ProductContractor, ProductSalaryWorker
from project.models import Project
from store.models import RawMaterial, Removed
from workers.models import Contractors, SalaryWorkers
from django.db.models import Sum
from datetime import datetime
from django.db.models.functions import TruncDate


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
class QuotationSerializer(ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["quotation"] = [
            f"{i + 1}. {item['name']} - {item['quantity']}"
            for i, item in enumerate(data["quotation"])
        ]
        return data

    class Meta:
        model = Quotation
        fields = "__all__"


class ProductContractorSerializer(serializers.ModelSerializer):
    contractor = ContractorsSerializer()

    class Meta:
        model = ProductContractor
        fields = ["contractor", "cost"]


class ProductSalaryWorkerSerializer(serializers.ModelSerializer):
    salary_worker = SalaryWorkersSerializer()

    class Meta:
        model = ProductSalaryWorker
        fields = ["salary_worker", "cost"]


class ProductSerializer(serializers.ModelSerializer):
    contractors = ProductContractorSerializer(source="productcontractor_set", many=True, read_only=True)
    salary_workers = ProductSalaryWorkerSerializer(source="productsalaryworker_set", many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "quantity", "images", "dimensions", "colour", "design",
            "contractors", "salary_workers", "selling_price", "cost_price", "total_production_cost", "profit"
        ]

    def create(self, validated_data):
        contractors_data = self.context["request"].data.get("contractors", [])
        salary_workers_data = self.context["request"].data.get("salary_workers", [])

        product = Product.objects.create(**validated_data)

        # Bulk create contractors & salary workers (more efficient)
        ProductContractor.objects.bulk_create(
            [ProductContractor(product=product, **contractor) for contractor in contractors_data]
        )
        ProductSalaryWorker.objects.bulk_create(
            [ProductSalaryWorker(product=product, **salary_worker) for salary_worker in salary_workers_data]
        )

        return product

    def update(self, instance, validated_data):
        contractors_data = self.context["request"].data.get("contractors", [])
        salary_workers_data = self.context["request"].data.get("salary_workers", [])

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Efficiently update contractors (avoid deleting everything)
        current_contractors = {pc.contractor.id: pc for pc in instance.productcontractor_set.all()}
        for contractor in contractors_data:
            contractor_id = contractor.get("contractor")
            if contractor_id in current_contractors:
                current_contractors[contractor_id].cost = contractor["cost"]
                current_contractors[contractor_id].save()
            else:
                ProductContractor.objects.create(product=instance, **contractor)

        # Efficiently update salary workers
        current_salary_workers = {psw.salary_worker.id: psw for psw in instance.productsalaryworker_set.all()}
        for salary_worker in salary_workers_data:
            worker_id = salary_worker.get("salary_worker")
            if worker_id in current_salary_workers:
                current_salary_workers[worker_id].cost = salary_worker["cost"]
                current_salary_workers[worker_id].save()
            else:
                ProductSalaryWorker.objects.create(product=instance, **salary_worker)

        return instance


class RawMaterialUsedSerializer(ModelSerializer):
    class Meta:
        model = RawMaterialUsed
        fields = '__all__'


# ##################################################


# store
class RawMaterialSerializer(ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = '__all__'


class ProjectSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class RemovedSerializer(ModelSerializer):
    class Meta:
        model = Removed
        fields = '__all__'