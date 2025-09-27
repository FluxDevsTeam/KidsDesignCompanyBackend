from rest_framework import serializers
from .models import Quotation, Product, ProductContractor, ProductSalaryWorker
from apps.store.models import Removed 
from apps.workers.serializers import SimpleContractorsSerializer, SimpleSalaryWorkersSerializer
from django.db.models import ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.db.models.fields import DecimalField
from django.shortcuts import get_object_or_404
from .models import Contractors, SalaryWorkers, Project


class ExpenseProductSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "project", "quantity", "name",]

    def get_project(self, obj):
        from apps.project.serializers import SimpleProjectSerializer
        return SimpleProjectSerializer(obj.project).data


class ProductRawMaterialRemovedSerializer(serializers.ModelSerializer):
    from apps.store.serializers import SimpleRawMaterialSerializer
    SimpleRawMaterialSerializer(source="material", read_only=True)
        

    class Meta:
        model = Removed
        fields = ["id", "raw_material", "name", "quantity", "price", "product_its_used", "date"]
        read_only_fields = ["id"]


class AggregatedRawMaterialSerializer(serializers.Serializer):
    from apps.store.serializers import SimpleRawMaterialSerializer
    raw_material = SimpleRawMaterialSerializer(source="material", read_only=True)
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    date = serializers.DateField(allow_null=True)


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

class SimpleProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ["id", "quantity", "name"]


class RawMaterialUsedSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    material__name = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)



class ProductContractorSerializer(serializers.ModelSerializer):
    linked_contractor = SimpleContractorsSerializer(source="contractor", read_only=True)

    class Meta:
        model = ProductContractor
        fields = ["id", "product", "contractor", "linked_contractor", "cost", "date"]
        read_only_fields = ['id', 'product']


class ProductSalaryWorkerSerializer(serializers.ModelSerializer):
    linked_salary_worker = SimpleSalaryWorkersSerializer(source="salary_worker", read_only=True)

    class Meta:
        model = ProductSalaryWorker
        fields = ["id", "product", "salary_worker", "linked_salary_worker", "date"]
        read_only_fields = ['id', 'product']


class ProductSerializer(serializers.ModelSerializer):
    from apps.project.serializers import SimpleProjectSerializer
    from apps.expensis.serializers import SimpleExpenseSerializer
    from apps.store.serializers import RawMaterialSerializer
    contractors = ProductContractorSerializer(source="productcontractor_set", many=True, read_only=True)
    salary_workers = ProductSalaryWorkerSerializer(source="productsalaryworker_set", many=True, read_only=True)
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.filter(archived=False, is_delivered=False),
        required=False,
        allow_null=True,
        write_only=True
    )
    linked_project = SimpleProjectSerializer(source="project", read_only=True)
    raw_materials = serializers.SerializerMethodField()
    quotation = QuotationSerializer(source="quotation_set", many=True, read_only=True)
    expensis = SimpleExpenseSerializer(source="expense_set", many=True, read_only=True)
    calculations = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "project", "quantity", "linked_project", "raw_materials", "expensis", "quotation", "name", "images", "sketch",
            "dimensions", "colour", "design", "production_note", "progress", "contractors", "salary_workers",
            "tasks", "selling_price", "overhead_cost", "overhead_cost_base_at_creation", "calculations"
        ]
        read_only_fields = ['overhead_cost_base_at_creation']

    def get_raw_materials(self, obj):
        removed_items = obj.removed_set.all()
        material_price_dict = {}
        for item in removed_items:
            material_id = item.material.id
            price = item.price
            key = (material_id, price)
            if key not in material_price_dict:
                material_price_dict[key] = {
                    'material': item.material,
                    'name': item.name,
                    'quantity': 0,
                    'price': price,
                    'date': item.date,
                }
            material_price_dict[key]['quantity'] += item.quantity
            if item.date and (not material_price_dict[key]['date'] or item.date > material_price_dict[key]['date']):
                material_price_dict[key]['date'] = item.date

        aggregated_data = [
            {
                'material': item['material'],
                'name': item['name'],
                'quantity': item['quantity'],
                'price': item['price'],
                'date': item['date'],
            }
            for item in material_price_dict.values()
        ]
        aggregated_data.sort(key=lambda x: x['material'].id)
        return AggregatedRawMaterialSerializer(aggregated_data, many=True).data

    def get_calculations(self, obj):
        return {
            "total_raw_material_cost": self.get_total_raw_material_cost(obj),
            "total_artisan_cost": self.get_total_artisan_cost(obj),
            "total_overhead_cost": self.get_total_overhead_cost(obj),
            "other_expensis": self.get_other_expensis(obj),
            "total_production_cost": self.get_total_production_cost(obj),
            "profit": self.get_profit(obj),
            "quantity": obj.quantity,
            "total_per_item": self.get_total_per_item(obj),
            "profit_per_item": self.get_profit_per_item(obj),
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

    def get_other_expensis(self, obj):
        expensis = obj.expense_set.filter(product=obj).annotate(total_cost=ExpressionWrapper(F("amount"), output_field=DecimalField(max_digits=10, decimal_places=2))).aggregate(total=Coalesce(Sum("total_cost"), Decimal(0)))
        return expensis['total']

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


