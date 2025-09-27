from django.db import transaction
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, F
from django.db.models.functions import Round
from django.db.models import IntegerField

from .models import InventoryItem, Sold, InventoryCategory, AddStock
from .serializers import (
    InventoryItemSerializer, SoldSerializer, InventoryCategorySerializer,
    AddSockSerializer
)
from .filters import InventoryItemFilter, AddStockFilter, SoldFilter
from api.utils import swagger_helper
from api.permissions import CheckUserRoles

class ApiInventoryItem(ModelViewSet):
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = InventoryItemFilter
    search_fields = ['name', 'description']
    pagination_class = PageNumberPagination

    permission_classes = [CheckUserRoles]
    required_roles = ['shopkeeper', 'ceo']

    def get_queryset(self):
        qs = super().get_queryset()
        if 'archived' not in self.request.query_params:
            qs = qs.filter(archived=False)
        return qs

    @swagger_helper("Inventory Items", "Inventory Item")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Inventory Items", "Inventory Item")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Inventory Items", "Inventory Item")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Inventory Items", "Inventory Item")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Inventory Items", "Inventory Item")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_helper("Inventory Items", "Inventory Item")
    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            AddStock.objects.create(item=instance, name=instance.name, cost_price=instance.cost_price, quantity=instance.stock)


    @swagger_helper("Inventory Items", "Inventory Item")
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        total_stock_count = queryset.count()
        total_stock_value = queryset.aggregate(
            total_stock_value=Coalesce(Sum(F('stock') * F('selling_price')), 0.0, output_field=DecimalField())
        )['total_stock_value'] or 0.0

        total_cost_value = queryset.aggregate(
            total_cost_value=Coalesce(Sum(F('stock') * F('cost_price')), 0.0, output_field=DecimalField())
        )['total_cost_value'] or 0.0

        total_profit = total_stock_value - total_cost_value

        page = self.paginate_queryset(queryset)
        if page is not None:
            serialized_items = self.get_serializer(page, many=True).data
        else:
            serialized_items = self.get_serializer(queryset, many=True).data

        response_data = {
            "total_stock_count": total_stock_count,
            "total_stock_value": float(total_stock_value),
            "total_cost_value": float(total_cost_value),
            "total_profit": float(total_profit),
            # "category_data": category_data,
            "items": serialized_items,
        }

        if page is not None:
            return self.get_paginated_response(response_data)
        return Response(response_data)


class ApiAddStock(ModelViewSet):
    serializer_class = AddSockSerializer
    queryset = AddStock.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AddStockFilter
    search_fields = ["item__name"]
    permission_classes = [CheckUserRoles]
    required_roles = ['shopkeeper','ceo']

    @swagger_helper("Stock Additions", "Stock Addition")
    def perform_create(self, serializer):
        item_id = self.request.data.get("item")
        quantity = self.request.data.get("quantity")

        if not item_id:
            raise ValueError("Please input a valid item.")

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
        except (ValueError, TypeError):
            raise ValueError("Invalid quantity.")

        item = get_object_or_404(InventoryItem, id=item_id)

        with transaction.atomic():
            item.stock += quantity
            item.save()

            serializer.save(item=item, name=item.name, cost_price=item.cost_price)

    @swagger_helper("Stock Additions", "Stock Addition")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Stock Additions", "Stock Addition")
    def list(self, request, *args, **kwargs):
        today = timezone.now().date()
        queryset = self.get_queryset()
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_stock = filterset.qs.order_by('-date')

        yearly_added_stock_count = queryset.filter(date__year=today.year).count()
        yearly_added_total_cost_price = \
        queryset.filter(date__year=today.year).aggregate(total=Sum(F('quantity') * F("cost_price")))['total'] or 0.0
        monthly_added_stock_count = queryset.filter(date__month=today.month).count()
        monthly_added_total_cost_price = \
        queryset.filter(date__month=today.month).aggregate(total=Sum(F('quantity') * F("cost_price")))['total'] or 0.0

        # filters
        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)
        day = request.query_params.get('day', None)

        filtered = filtered_stock

        if day is not None and year is None and month is None:
            year = today.year
            month = today.month

        if year is None and month is None:
            year = today.year
            month = today.month

        if year is not None and month is None and day is None:
            filtered = filtered_stock.filter(date__year=year)

        elif year is not None and day is not None:
            if month is None:
                month = today.month
            filtered = filtered_stock.filter(date__year=year, date__month=month, date__day=day)

        elif year is not None and month is not None and day is None:
            filtered = filtered_stock.filter(date__year=year, date__month=month)

        elif year is not None and month is not None and day is not None:
            filtered = filtered_stock.filter(date__year=year, date__month=month, date__day=day)

        # Group by day
        daily_data = []
        current_date = None
        daily_entries = []

        for entry in filtered:
            entry_date = entry.date

            if entry_date != current_date:
                if daily_entries:
                    daily_data.append({
                        "date": current_date,
                        "entries": AddSockSerializer(daily_entries, many=True, context={'request': request}).data,
                        "daily_added_cost_total": sum(e.quantity * e.cost_price for e in daily_entries),
                    })
                current_date = entry_date
                daily_entries = [entry]
            else:
                daily_entries.append(entry)

        if daily_entries:
            daily_data.append({
                "date": current_date,
                "entries": AddSockSerializer(daily_entries, many=True, context={'request': request}).data,
                "daily_added_cost_total": sum(e.quantity * e.cost_price for e in daily_entries),
            })

        response_data = {
            "yearly_added_stock_count": yearly_added_stock_count,
            "yearly_added_total_cost_price": yearly_added_total_cost_price,
            "monthly_added_stock_count": monthly_added_stock_count,
            "monthly_added_total_cost_price": monthly_added_total_cost_price,
            "daily_added_cost_total": sum(e.quantity * e.cost_price for e in daily_entries),
            "daily_data": daily_data,
        }

        if year:
            yearly_total = queryset.filter(date__year=year).aggregate(total=Sum(F("quantity") * F("cost_price")))[
                               'total'] or 0.0
            response_data["yearly_total"] = yearly_total

        return Response(response_data)

    @swagger_helper("Stock Additions", "Stock Addition")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Stock Additions", "Stock Addition")
    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    @swagger_helper("Stock Additions", "Stock Addition")
    def partial_update(self, request, *args, **kwargs):
        quantity = request.data.get("quantity")
        date = request.data.get("date")

        if not quantity and not date:
            return Response({"error": "quantity or/and date required"})

        try:
            quantity = Decimal(quantity)  # Convert to Decimal
        except ValueError:
            return Response({"error": "Invalid quantity format"}, status=status.HTTP_400_BAD_REQUEST)

        if int(quantity) <= 0:
            return Response({"error": "quantity  most be a positive number"})

        added_stock = self.get_object()
        with transaction.atomic():
            if date:
                try:
                    added_stock.date = date
                    added_stock.save()
                except:
                    return Response(
                        {"error": "date format is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

            if added_stock.item:
                inventory_item = get_object_or_404(InventoryItem, id=added_stock.item.id)
                change = abs(added_stock.quantity - quantity)
                if added_stock.quantity > quantity:
                    if inventory_item.stock < change:
                        return Response({"data": "not enough stock remaining in inventory."})
                    inventory_item.stock -= change
                    added_stock.quantity -= change
                else:
                    inventory_item.stock += change
                    added_stock.quantity += change
                inventory_item.save()
                added_stock.save()
                return Response({"data": "quantity updated successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "inventory item has been deleted"})


    @swagger_helper("Stock Additions", "Stock Addition")
    def destroy(self, request, *args, **kwargs):
        added_item = self.get_object()
        if added_item.item is not None:
            inventory_item = get_object_or_404(InventoryItem, id=added_item.item.id)
            inventory_item.stock -= added_item.quantity
            inventory_item.save()
            added_item.delete()
            return Response({"message": "stock add record deleted and inventory item updated."}, status=204)

        added_item.delete()
        return Response(
            {"message": "stock add record deleted but inventory item not updated because it no longer exists."},
            status=204)


class ApiInventoryCategory(ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    # permission_classes = [IsCEO | IsProjectManager]
    permission_classes = [CheckUserRoles]
    required_roles = ['shopkeeper','ceo']
    filter_backends = [SearchFilter]
    search_fields = ['name']

    @swagger_helper("Inventory Categories", "Inventory Category")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Inventory Categories", "Inventory Category")
    def list(self, request, *args, **kwargs):
        """Override list to disable pagination."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_helper("Inventory Categories", "Inventory Category")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Inventory Categories", "Inventory Category")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Inventory Categories", "Inventory Category")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
        
    @swagger_helper("Inventory Categories", "Inventory Category")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiSold(ModelViewSet):
    serializer_class = SoldSerializer
    queryset = Sold.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = SoldFilter
    search_fields = ['item__name', 'customer__name']
    permission_classes = [CheckUserRoles]
    required_roles = ['shopkeeper', 'ceo', 'admin', 'accountant']

    @swagger_helper("Sold Items", "Sold Item")
    def list(self, request, *args, **kwargs):
        try:
            today = timezone.now().date()
            filtered_sold = self.filter_queryset(self.get_queryset()).order_by('-date')

            this_month_sold = filtered_sold.filter(date__year=today.year, date__month=today.month)
            this_year_sold = filtered_sold.filter(date__year=today.year)
            this_year_sold_count = filtered_sold.filter(date__year=today.year).count()
            this_month_sold_count = this_month_sold.count()
            this_month_sales = this_month_sold.aggregate(total=Sum(F("selling_price") * F("quantity")))["total"] or Decimal('0.00')
            this_year_sales = this_year_sold.aggregate(total=Sum(F("selling_price") * F("quantity")))["total"] or Decimal('0.00')
            this_month_profit = this_month_sold.aggregate(total=Sum((F("selling_price") * F("quantity")) - (F("cost_price") * F("quantity")),output_field=DecimalField(max_digits=10, decimal_places=2)))["total"] or Decimal('0.00')
            this_year_profit = this_year_sold.aggregate(total=Sum((F("selling_price") * F("quantity")) - (F("cost_price") * F("quantity")),output_field=DecimalField(max_digits=10, decimal_places=2)))["total"] or Decimal('0.00')
            this_month_project_sales = this_month_sold.filter(logistics=None).aggregate(total=Sum(F("selling_price") * F("quantity")))["total"] or Decimal('0.00')
            this_month_non_project_sales = this_month_sold.filter(project=None).aggregate(total=Sum(F("selling_price") * F("quantity")))["total"] or Decimal('0.00')

            year = request.query_params.get('year', None)
            month = request.query_params.get('month', None)


            daily_data = []
            current_date = None
            daily_solds = []
            if year is None and month is None:
                filtered_sold = filtered_sold.filter(date__year=today.year, date__month=today.month)
            if year is None and month is not None:
                filtered_sold = filtered_sold.filter(date__year=today.year, date__month=month)
            if year is not None and month is None:
                filtered_sold = filtered_sold.filter(date__year=year, date__month=today.month)

            for sold in filtered_sold:
                sold_date = sold.date.date() if isinstance(sold.date, datetime) else sold.date

                if current_date != sold_date:
                    if daily_solds:
                        daily_data.append({
                            "date": current_date,
                            "entries": self.get_serializer(daily_solds, many=True, context={'request': request}).data,
                            "daily_total": float(sum(s.total_price for s in daily_solds)),
                        })
                    current_date = sold_date
                    daily_solds = [sold]
                else:
                    daily_solds.append(sold)

            if daily_solds:
                daily_data.append({
                    "date": current_date,
                    "entries": self.get_serializer(daily_solds, many=True, context={'request': request}).data,
                    "daily_total": float(sum(s.total_price for s in daily_solds)),
                })

            response_data = {
                "this_year_sold_count": this_year_sold_count,
                "this_month_sales_count": this_month_sold_count,
                "this_year_sales": float(this_year_sales),
                "this_month_sales": float(this_month_sales),
                "this_year_profit": float(this_year_profit),
                "this_month_profit": float(this_month_profit),
                "this_month_project_sales": float(this_month_project_sales),
                "this_month_non_project_sales": float(this_month_non_project_sales),
                "daily_data": daily_data,
            }

            return Response(response_data)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


    @swagger_helper("Sold Items", "Sold Item")
    def create(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")
        customer = request.data.get("customer")
        project = request.data.get("project")
        logistics = request.data.get("logistics")

        if bool(customer) == bool(project):
            if not customer:
                return Response({"error": "Either 'customer' or 'project' is required."},
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "Only one of 'customer' or 'project' is allowed."},
                                status=status.HTTP_400_BAD_REQUEST)

        if project and logistics:
            return Response(
                {"error": "you cant set logistics for item sold in a project"}, status=status.HTTP_400_BAD_REQUEST)

        if (customer and (not logistics)) or (logistics and (not customer)):
            return Response(
                {"error": "both 'customer' and 'logistics' is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not item_id or not quantity:
            return Response(
                {"error": "'item', and 'quantity' are both required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            return Response(
                {"error": "'quantity' must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        inventory_item = get_object_or_404(InventoryItem, id=item_id)
        if quantity > inventory_item.stock:
            return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)
        if project:
            project_instance = get_object_or_404(Project, id=project)
            customer = project_instance.customer
            Sold.objects.create(item=inventory_item, quantity=quantity, customer=customer,
                                cost_price=inventory_item.cost_price, selling_price=inventory_item.selling_price,
                                project=project_instance, name=inventory_item.name)
        else:
            customer_data = get_object_or_404(Customer, id=customer)
            Sold.objects.create(item=inventory_item, quantity=quantity, customer=customer_data,
                                cost_price=inventory_item.cost_price, selling_price=inventory_item.selling_price,
                                logistics=logistics, name=inventory_item.name)

        inventory_item.stock -= quantity
        inventory_item.save()
        return Response({"message": "Sale completed successfully."}, status=status.HTTP_200_OK)

    @swagger_helper("Sold Items", "Sold Item")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Sold Items", "Sold Item")
    def destroy(self, request, *args, **kwargs):
        sold_item = self.get_object()
        if sold_item.item is not None:
            inventory_item = get_object_or_404(InventoryItem, pk=sold_item.item.id)
            inventory_item.stock += sold_item.quantity
            inventory_item.save()
            sold_item.delete()
            return Response({"message": "Sold item deleted and inventory updated."}, status=204)

        sold_item.delete()
        return Response({
                            "message": "Sold item deleted but inventory not updated because item has beed deleted. you can create an invcentory again and add it manually."},
                        status=204)

    @swagger_helper("Sold Items", "Sold Item")
    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    @swagger_helper("Sold Items", "Sold Item")
    def partial_update(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")
        project = request.data.get("project")
        customer = request.data.get("customer")
        logistics = request.data.get("logistics")
        date = request.data.get("date")
        sold_item = self.get_object()

        if date:
            try:
                sold_item.date = date
                sold_item.save()
            except:
                return Response(
                    {"error": "date format is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        if (customer and (not logistics)) and (logistics and (not customer)) and (
                customer and (not sold_item.logistics)) and (logistics and (not sold_item.customer)):
            return Response(
                {"error": "both 'customer' and 'logistics' is required."}, status=status.HTTP_400_BAD_REQUEST)

        if (((project and logistics) or (project and sold_item.logistics) or (sold_item.project and logistics)) and (
        not customer) and project) and (project and (logistics or customer)):
            return Response(
                {"error": "you cant set logistics for item sold in a project"}, status=status.HTTP_400_BAD_REQUEST)

        if customer and project:
            return Response(
                {"error": "only one of either 'customer' or 'project' is required."},
                status=status.HTTP_400_BAD_REQUEST)
        if project:
            project_db = get_object_or_404(Project, id=int(project))
            project = project_db

        if customer:
            customer_db = get_object_or_404(Customer, id=int(customer))
            customer = customer_db

        if all(field is None for field in [item_id, quantity, project, customer, logistics]):
            return Response(
                {
                    "error": "At least one of 'item', 'quantity', 'cost_price', 'selling_price', 'customer', 'logistics' or 'project' is required."},
                status=status.HTTP_400_BAD_REQUEST)

        if quantity is not None:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    return Response({"error": "Quantity must be a positive number."},
                                    status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "quantity most be a number"}, status=status.HTTP_400_BAD_REQUEST)

        if logistics is not None:
            try:
                logistics = float(logistics)
                if logistics <= 0:
                    return Response({"error": "logistics must be a positive number."},
                                    status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "logistics most be a number"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if item_id and int(item_id) != int(sold_item.item.id):
                updated_fields = []
                old_inventory_item = get_object_or_404(InventoryItem, id=sold_item.item.id)
                old_inventory_item.stock += sold_item.quantity

                new_inventory_item = get_object_or_404(InventoryItem, id=item_id)
                if quantity is None:
                    quantity = sold_item.quantity
                if quantity > new_inventory_item.stock:
                    return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)

                if project and project != sold_item.project:
                    sold_item.project = project
                    sold_item.customer = None
                    sold_item.logistics = None
                    updated_fields.append("project")

                if customer and customer != sold_item.customer:
                    sold_item.project = None
                    sold_item.customer = customer
                    updated_fields.append("customer")

                if logistics and logistics != sold_item.logistics:
                    sold_item.logistics = logistics
                    updated_fields.append("logistics")

                old_inventory_item.save()
                new_inventory_item.stock -= quantity
                new_inventory_item.save()

                sold_item.item = new_inventory_item
                sold_item.quantity = quantity
                sold_item.cost_price = new_inventory_item.cost_price
                sold_item.selling_price = new_inventory_item.selling_price
                sold_item.name = new_inventory_item.name
                sold_item.save()
                updated_fields.append("Sales")

                return Response({"data": f"{', '.join(updated_fields)} updated successfully"},
                                status=status.HTTP_200_OK)

            if quantity is not None and quantity != sold_item.quantity:
                inventory_item = get_object_or_404(InventoryItem, id=sold_item.item.id)
                difference = abs(quantity - sold_item.quantity)
                updated_fields = []
                if quantity > sold_item.quantity:
                    if difference > inventory_item.stock:
                        return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)
                    inventory_item.stock -= difference
                else:
                    inventory_item.stock += difference

                if project and project != sold_item.project:
                    sold_item.project = project
                    sold_item.customer = None
                    sold_item.logistics = None
                    updated_fields.append("project")

                if customer and customer != sold_item.customer:
                    sold_item.project = None
                    sold_item.customer = customer
                    updated_fields.append("customer")

                if logistics and logistics != sold_item.logistics:
                    sold_item.logistics = logistics
                    updated_fields.append("logistics")

                inventory_item.save()
                sold_item.quantity = quantity
                sold_item.save()
                updated_fields.append("Quantity")

                return Response({"data": f"{', '.join(updated_fields)} updated successfully"},
                                status=status.HTTP_200_OK)
            updated_fields = []

            if project and project != sold_item.project:
                sold_item.project = project
                sold_item.customer = None
                sold_item.logistics = None
                updated_fields.append("project")

            if customer and customer != sold_item.customer:
                sold_item.project = None
                sold_item.customer = customer
                updated_fields.append("customer")

            if logistics and logistics != sold_item.logistics:
                sold_item.logistics = logistics
                updated_fields.append("logistics")

            if updated_fields:
                sold_item.save()
                return Response({"data": f"{', '.join(updated_fields)} updated successfully"},
                                status=status.HTTP_200_OK)

            return Response({"message": "No changes made."}, status=status.HTTP_200_OK)

