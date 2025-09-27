from rest_framework import serializers
from .models import Customer
# from apps.project.serializers import SimpleProjectSerializer # Removed to fix circular import
# from apps.shop.serializers import SimpleSoldSerializer # Removed to fix circular import

class SimpleCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name']
        read_only_fields = ['id']


class CustomerSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    shop_item = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone_number", "address", "project", "shop_item", "created_at"]
        read_only_fields = ["id"]

    def get_project(self, obj):
        from apps.project.serializers import SimpleProjectSerializer
        project = obj.project_set.first()
        return SimpleProjectSerializer(project).data if project else None

    def get_shop_item(self, obj):
        from apps.shop.serializers import SimpleSoldSerializer
        shop_item = obj.sold_set.first()
        return SimpleSoldSerializer(shop_item).data if shop_item else None


class CustomerDetailSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    shop_item = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone_number", "address", "project", "shop_item", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_project(self, obj):
        from apps.project.serializers import SimpleProjectSerializer
        project = obj.project_set.all()
        return SimpleProjectSerializer(project, many=True).data if project else None

    def get_shop_item(self, obj):
        from apps.shop.serializers import SimpleSoldSerializer
        shop_item = obj.sold_set.all()
        return SimpleSoldSerializer(shop_item, many=True).data if shop_item else None
