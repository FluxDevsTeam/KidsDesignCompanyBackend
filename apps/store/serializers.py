from rest_framework.serializers import ModelSerializer
from .models import RawMaterial, Removed, StoreCategory, AddRawMaterials
# from apps.products.serializers import SimpleProductSerializer # Removed to fix circular import
# from apps.products.serializers import SimpleRawMaterialSerializer # Removed

# class ProductRawMaterialRemovedSerializer(ModelSerializer): # This class should be in products.serializers
#     raw_material = SimpleRawMaterialSerializer(source="material", read_only=True)

#     class Meta:
#         model = Removed
#         fields = ["id", "raw_material", "name", "quantity", "price", "product_its_used", "date"]
#         read_only_fields = ["id"]


class SimpleRawMaterialSerializer(ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = ["id", "name", "unit"]
        read_only_fields = ["id"]


class StoreCategorySerializer(ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class RawMaterialSerializer(ModelSerializer):
    from .serializers import StoreCategorySerializer
    store_category = StoreCategorySerializer(source="category", read_only=True) # Modified

    class Meta:
        model = RawMaterial
        fields = ["id", "name", "unit", "quantity", "price", "category", "store_category", "archived", "description", "image", ]
        read_only_fields = ["id"]


class RemovedSerializer(ModelSerializer):
    
    from apps.products.serializers import SimpleProductSerializer
    from .serializers import SimpleRawMaterialSerializer 
    product_its_used = SimpleProductSerializer(source="product", read_only=True) # Modified
    raw_material = SimpleRawMaterialSerializer(source="material", read_only=True) # Modified

    class Meta:
        model = Removed
        fields = ["id", "material", "raw_material", "name", "quantity", "price", "product", "product_its_used", "date"]
        read_only_fields = ["id"]
        extra_kwargs = {'material': {'write_only': True}, 'product': {'write_only': True}}


class AddRawMaterialsSerializer(ModelSerializer):
    from .serializers import SimpleRawMaterialSerializer # Correct local import
    material = SimpleRawMaterialSerializer(source="item", read_only=True) # Modified

    class Meta:
        model = AddRawMaterials
        fields = ["id", "item", "material", "quantity", "cost_price", "date"]
        read_only_fields = ["id"]
        extra_kwargs = {'item': {'write_only': True}}

