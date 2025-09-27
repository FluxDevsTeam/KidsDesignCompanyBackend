from rest_framework import serializers
from .models import Expense, ExpenseCategory, Assets
# from apps.project.serializers import SimpleProjectSerializer # Removed to fix circular import

# from apps.shop.serializers import SimpleSoldSerializer # Removed to fix circular import
from apps.products.serializers import ExpenseProductSerializer



class SimpleExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['name', 'amount', 'quantity', 'date']


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name']
        read_only_fields = ['id']


class ExpenseSerializer(serializers.ModelSerializer):
    from apps.project.serializers import SimpleProjectSerializer
    from apps.shop.serializers import SimpleSoldSerializer
    from apps.products.serializers import ExpenseProductSerializer 
        
    expense_category = ExpenseCategorySerializer(source="category", read_only=True)
    linked_project = SimpleProjectSerializer(source="project", read_only=True) # Removed, already in __init__
    sold_item = SimpleSoldSerializer(source="shop", read_only=True) # Removed, already in __init__
    linked_product = ExpenseProductSerializer(source="product", read_only=True) # Removed, moved to __init__

    class Meta:
        model = Expense
        fields = ['id', 'name', 'category', 'expense_category', 'asset', 'description', 'project', 'shop', 'linked_project',
                  'linked_product', 'product', 'sold_item', 'amount', 'quantity', 'payment_method', 'date']
        read_only_fields = ['id']
        extra_kwargs = {'category': {'write_only': True}, 'project': {'write_only': True}, 'product': {'write_only': True}, 'shop': {'write_only': True}}

    def validate(self, attrs):
        project_provided = 'project' in attrs
        shop_provided = 'shop' in attrs
        product_provided = 'product' in attrs
        if self.partial:
            if project_provided and not shop_provided and not product_provided:
                attrs['shop'] = None
                attrs['product'] = None
            elif shop_provided and not project_provided and not product_provided:
                attrs['project'] = None
                attrs['product'] = None
            elif product_provided and not project_provided and not shop_provided:
                attrs['project'] = None
                attrs['shop'] = None
        project = attrs.get('project')
        shop = attrs.get('shop')
        product = attrs.get('product')
        if project and shop and product or project and shop or project and product or shop and product:
            raise serializers.ValidationError(
                "Expense cannot be associated with more than 1 of project, shop item and product."
            )
        return attrs


class AssetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assets
        fields = ["id", 'name', 'value', 'expected_lifespan', 'is_still_available', "date_added", "end_date", "note"]
        read_only_fields = ["id"]