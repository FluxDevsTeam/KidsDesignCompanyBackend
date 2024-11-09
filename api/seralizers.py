from rest_framework.fields import SerializerMethodField

from shop.models import InventoryItem, Sold
from rest_framework import serializers

#
# class CitiesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Cities
#         fields = '__all__'
#
#
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
#
# class RouteViewSerializer(serializers.ModelSerializer):
#     origin = CitiesSerializer(read_only=True)
#     destination = CitiesSerializer(read_only=True)
#
#     class Meta:
#         model = Route
#         fields = ['departure_date', 'departure_time', 'origin', 'destination', 'price']
#
#
# class PendingSerializer(serializers.ModelSerializer):
#     flight = RouteViewSerializer(read_only=True)
#
#     class Meta:
#         model = Pending
#         fields = ['id', 'flight', 'no_of_passengers', 'total_cost']
#         read_only_fields = ['total_cost', ]
#
#
# class CreatePendingSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Pending
#         fields = ['id', 'flight', 'no_of_passengers', 'total_cost']
#         read_only_fields = ['total_cost', ]
#
#
# class EditPendingSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Pending
#         fields = ['flight', 'no_of_passengers']
#
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
