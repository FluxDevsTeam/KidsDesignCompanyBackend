from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
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
        fields = ['id', 'quantity', 'date', 'updated_on', 'customer', 'item', 'total_price', 'profit']
        read_only_fields = ['id', 'updated_on']


class CustomerSerializer(ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


from rest_framework import serializers
from .models import Expense
from django.db.models import Sum
from datetime import datetime


class ExpenseSerializer(serializers.ModelSerializer):
    daily_total = serializers.SerializerMethodField()
    monthly_total = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = ['id', 'name', 'description', 'amount', 'quantity', 'date', 'daily_total', 'monthly_total']
        read_only_fields = ['id', 'date']

    def get_daily_total(self, obj):
        """
        Calculate daily total for the expense entries grouped by day.
        """
        date = obj.date.date()  # Just the date part of the datetime
        total = Expense.objects.filter(date__date=date).aggregate(Sum('amount'))['amount__sum']
        return total or 0.0

    def get_monthly_total(self, obj):
        """
        Calculate the monthly total for the current month.
        """
        current_month = datetime.now().month
        current_year = datetime.now().year
        total = Expense.objects.filter(date__month=current_month, date__year=current_year).aggregate(Sum('amount'))[
            'amount__sum']
        return total or 0.0

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
