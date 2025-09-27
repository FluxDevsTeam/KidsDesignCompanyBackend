from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import InventoryItem, Sold, InventoryCategory, AddStock
from apps.project.serializers import SimpleProjectSerializer
from apps.customers.serializers import SimpleCustomerSerializer

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



class SoldSerializer(serializers.ModelSerializer):
    item_sold = SimpleInventoryItemSerializer(source="item", read_only=True)
    sold_to = SimpleCustomerSerializer(source="customer", read_only=True)
    linked_project = SimpleProjectSerializer(source="project", read_only=True)

    def __init__(self, *args, **kwargs):
        from apps.customers.serializers import SimpleCustomerSerializer
        self.__class__.sold_to = SimpleCustomerSerializer(source="customer", read_only=True)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Sold
        fields = ['id', 'quantity', 'date', 'updated_on', 'customer', 'sold_to', 'project', 'linked_project', 'item',
                  'name', 'item_sold', 'logistics', 'cost_price', 'selling_price', 'total_price', 'profit']
        read_only_fields = ['id', 'updated_on', 'selling_price', 'cost_price', 'name']
        extra_kwargs = {'customer': {'write_only': True}, 'item': {'write_only': True}, 'project': {'write_only': True}}


class SimpleSoldSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = Sold
        fields = ['id', 'name', 'quantity', 'cost_price', 'selling_price', 'total_price']


class AddSockSerializer(ModelSerializer):
    inventory_item = SimpleInventoryItemSerializer(source="item", read_only=True)

    class Meta:
        model = AddStock
        fields = ["id", "item", "inventory_item", "name", "quantity", "cost_price", "date"]
        extra_kwargs = {'item': {'write_only': True}}
        read_only_fields = ['id', 'name', 'cost_price']
