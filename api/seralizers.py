from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
from shop.models import InventoryItem, Sold
from customers.models import Customer
from expensis.models import Expense
from products.models import Quotation, RawMaterialUsed, Product
from project.models import Project
from store.models import RawMaterial, Removed
from workers.models import Contractors, SalaryWorkers


class InventoryItemSerializer(ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'


class SoldSerializer(ModelSerializer):
    class Meta:
        model = Sold
        fields = '__all__'


class CustomerSerializer(ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class ExpenseSerializer(ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'


class QuotationSerializer(ModelSerializer):
    class Meta:
        model = Quotation
        fields = '__all__'


class ProjectSerializer(ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class RawMaterialSerializer(ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = '__all__'


class RawMaterialUsedSerializer(ModelSerializer):
    class Meta:
        model = RawMaterialUsed
        fields = '__all__'


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class RemovedSerializer(ModelSerializer):
    class Meta:
        model = Removed
        fields = '__all__'


class ContractorsSerializer(ModelSerializer):
    class Meta:
        model = Contractors
        fields = '__all__'


class SalaryWorkersSerializer(ModelSerializer):
    class Meta:
        model = SalaryWorkers
        fields = '__all__'


# class SearchSerializer(serializers.ModelSerializer):
#     no_of_passengers = serializers.IntegerField(default=1)
#
#     class Meta:
#         model = Route
#         fields = ['origin', 'destination', 'departure_date','no_of_passengers' ]
#
#
# class RouteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Route
#         fields = '__all__'
#         read_only_fields = ['tickets_sold', 'is_seat_remaining']
#
# class PendingSerializer(serializers.ModelSerializer):
#     flight = RouteViewSerializer(read_only=True)
#
#     class Meta:
#         model = Pending
#         fields = ['id', 'flight', 'no_of_passengers', 'total_cost']
#         read_only_fields = ['total_cost', ]
#
# class BookingSerializer(serializers.ModelSerializer):
#     flight = RouteViewSerializer(read_only=True)
#     passenger_name = SerializerMethodField(method_name='get_passenger_name')
#
#     class Meta:
#         model = Booking
#         fields = ['owner', 'passenger_name', 'flight_no', 'flight', 'no_of_passengers', 'check_in', 'total_cost',
#                   'placed_at']
#         read_only_fields = ['owner', 'total_cost']
#
#     def get_passenger_name(self, obj):
#         owner = obj.owner
#         return f"{owner.first_name} {owner.last_name}"
#
#
#
#
