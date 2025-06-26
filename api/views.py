from django.db import transaction
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .pagination import AssetsPagination
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .seralizers import InventoryItemSerializer, SoldSerializer, CustomerSerializer, ExpenseSerializer, \
    QuotationSerializer, ProductSerializer, RawMaterialSerializer, ProjectSerializer, RawMaterialUsedSerializer, \
    RemovedSerializer, ContractorsSerializer, SalaryWorkersSerializer, ExpenseCategorySerializer, AddSockSerializer, \
    InventoryCategorySerializer, ProductSalaryWorkerSerializer, ProductContractorSerializer, StoreCategorySerializer, \
    SalaryWorkersRecordSerializer, ContractorRecordSerializer, OverheadCostSerializer, AssetsSerializer, \
    AddRawMaterialsSerializer, OtherProductionSerializer, PaidSerializer, CustomerDetailSerializer
from shop.models import InventoryItem, Sold, InventoryCategory, AddStock
from customers.models import Customer
from expensis.models import Expense, ExpenseCategory, Assets
from products.models import Quotation, Product, ProductSalaryWorker, ProductContractor
from project.models import Project, OverheadCost, OtherProduction
from store.models import RawMaterial, Removed, StoreCategory, AddRawMaterials
from workers.models import Contractors, SalaryWorkers, ContractorRecord, SalaryWorkersRecord, Paid
from rest_framework import viewsets, status, permissions, mixins
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from django.db.models import F, ExpressionWrapper, DecimalField, Sum
from django.db.models import Avg, IntegerField
from django.db.models.functions import Round, Cast, Coalesce
from .filters import ExpenseFilter, InventoryItemFilter, AddStockFilter, SoldFilter, ProjectFilter, \
    AddRawMaterialsFilter, PaidFilter, RawMaterialFilter, RemovedFilter
from .permissions import CheckUserRoles

User = get_user_model()


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

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            AddStock.objects.create(item=instance, name=instance.name, cost_price=instance.cost_price,
                                    quantity=instance.stock)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())  # ← applies search + filterset

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


class ApiAddRawMaterials(ModelViewSet):
    serializer_class = AddRawMaterialsSerializer
    queryset = AddRawMaterials.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AddRawMaterialsFilter
    search_fields = ['item__name']

    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper','ceo']

    def perform_create(self, serializer):
        item_id = self.request.data.get("item")
        quantity = self.request.data.get("quantity")
        cost_price = self.request.data.get("cost_price")
        if not item_id:
            raise ValueError("Please input a valid item.")

        try:
            quantity = Decimal(quantity)
            if quantity <= 0 or cost_price <= 0:
                raise ValueError("Quantity must be greater than zero.")
        except (ValueError, TypeError):
            raise ValueError("Invalid quantity.")

        item = get_object_or_404(RawMaterial, id=item_id)

        with transaction.atomic():
            item.quantity += quantity
            if cost_price != item.price:
                item.price = cost_price
                item.save()
                serializer.save(item=item, name=item.name, cost_price=cost_price)
            else:
                item.save()
                serializer.save(item=item, name=item.name, cost_price=item.price)

    def list(self, request, *args, **kwargs):
        today = timezone.now().date()
        queryset = self.get_queryset()
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_raw_material = filterset.qs.order_by('-date')

        yearly_added_material_count = queryset.filter(date__year=today.year).count()
        yearly_added_total_cost = \
        queryset.filter(date__year=today.year).aggregate(total=Sum(F('quantity') * F("cost_price")))['total'] or 0.0
        monthly_added_material_count = queryset.filter(date__month=today.month).count()
        monthly_added_total_cost = \
        queryset.filter(date__month=today.month).aggregate(total=Sum(F('quantity') * F("cost_price")))['total'] or 0.0

        # filters
        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)
        day = request.query_params.get('day', None)

        filtered = filtered_raw_material

        if day is not None and year is None and month is None:
            year = today.year
            month = today.month

        if year is None and month is None:
            year = today.year
            month = today.month

        if year is not None and month is None and day is None:
            filtered = filtered_raw_material.filter(date__year=year)

        elif year is not None and day is not None:
            if month is None:
                month = today.month
            filtered = filtered_raw_material.filter(date__year=year, date__month=month, date__day=day)

        elif year is not None and month is not None and day is None:
            filtered = filtered_raw_material.filter(date__year=year, date__month=month)

        elif year is not None and month is not None and day is not None:
            filtered = filtered_raw_material.filter(date__year=year, date__month=month, date__day=day)

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
                        "entries": AddRawMaterialsSerializer(daily_entries, many=True).data,
                        "daily_added_cost_total": sum(e.quantity * e.cost_price for e in daily_entries),
                    })
                current_date = entry_date
                daily_entries = [entry]
            else:
                daily_entries.append(entry)

        if daily_entries:
            daily_data.append({
                "date": current_date,
                "entries": AddRawMaterialsSerializer(daily_entries, many=True).data,
                "daily_added_cost_total": sum(e.quantity * e.cost_price for e in daily_entries),
            })

        response_data = {
            "yearly_added_material_count": yearly_added_material_count,
            "yearly_added_total_cost": yearly_added_total_cost,
            "monthly_added_material_count": monthly_added_material_count,
            "monthly_added_total_cost": monthly_added_total_cost,
            "daily_data": daily_data,
        }

        if year:
            yearly_total = queryset.filter(date__year=year).aggregate(total=Sum(F("quantity") * F("cost_price")))[
                               'total'] or 0.0
            response_data["yearly_total"] = yearly_total

        return Response(response_data)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        quantity = request.data.get("quantity")

        try:
            quantity = Decimal(quantity)
        except ValueError:
            return Response({"error": "Invalid quantity format"}, status=status.HTTP_400_BAD_REQUEST)

        if not quantity:
            return Response({"error": "quantity required"})

        if quantity <= 0:
            return Response({"error": "quantity  most be a positive number"})

        added_material = self.get_object()
        with transaction.atomic():
            if added_material.item:
                raw_material = get_object_or_404(RawMaterial, id=added_material.item.id)
                change = abs(added_material.quantity - quantity)
                if added_material.quantity > quantity:
                    if raw_material.quantity < change:
                        return Response({"data": "not enough stock remaining in inventory."})
                    raw_material.quantity -= change
                    added_material.quantity -= change
                else:
                    raw_material.quantity += change
                    added_material.quantity += change
                raw_material.save()
                added_material.save()
                return Response({"data": "quantity updated successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "raw material has been deleted. cant make any edits now"})

    def destroy(self, request, *args, **kwargs):
        added_item = self.get_object()
        if added_item.item is not None:
            raw_material = get_object_or_404(RawMaterial, id=added_item.item.id)
            raw_material.quantity -= added_item.quantity
            raw_material.save()
            added_item.delete()
            return Response({"message": "waw material add record deleted and raw material updated."}, status=204)

        added_item.delete()
        return Response(
            {"message": "add raw material record deleted but raw material not updated because it no longer exists."},
            status=204)


class ApiAddStock(ModelViewSet):
    serializer_class = AddSockSerializer
    queryset = AddStock.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AddStockFilter
    search_fields = ["item__name"]
    permission_classes = [CheckUserRoles]
    required_roles = ['shopkeeper','ceo']

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

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        quantity = request.data.get("quantity")

        if not quantity:
            return Response({"error": "quantity required"})

        try:
            quantity = Decimal(quantity)  # Convert to Decimal
        except ValueError:
            return Response({"error": "Invalid quantity format"}, status=status.HTTP_400_BAD_REQUEST)

        if int(quantity) <= 0:
            return Response({"error": "quantity  most be a positive number"})

        added_stock = self.get_object()
        with transaction.atomic():
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

    def list(self, request, *args, **kwargs):
        """Override list to disable pagination."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ApiStoreCategory(ModelViewSet):
    queryset = StoreCategory.objects.all()
    serializer_class = StoreCategorySerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'ceo']
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def list(self, request, *args, **kwargs):
        """Override list to disable pagination and apply search filters."""
        queryset = self.filter_queryset(self.get_queryset())  # Apply filter backends
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ApiSold(ModelViewSet):
    serializer_class = SoldSerializer
    queryset = Sold.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = SoldFilter
    search_fields = ['item__name', 'customer__name']
    permission_classes = [CheckUserRoles]
    required_roles = ['shopkeeper', 'ceo', 'admin']

    def list(self, request, *args, **kwargs):
        try:
            filtered_solds = self.filter_queryset(self.get_queryset()).order_by('-date')

            today = timezone.now().date()

            this_month_solds = filtered_solds.filter(date__year=today.year, date__month=today.month)
            this_month_sold_count = this_month_solds.count()
            this_month_sales = this_month_solds.aggregate(
                total=Sum(F("selling_price") * F("quantity"))
            )["total"] or Decimal('0.00')
            this_month_profit = this_month_solds.aggregate(
                total=Sum(
                    (F("selling_price") * F("quantity")) - (F("cost_price") * F("quantity")),
                    output_field=DecimalField(max_digits=10, decimal_places=2)))["total"] or Decimal('0.00')
            this_month_project_sales = this_month_solds.filter(logistics=None).aggregate(
                total=Sum(F("selling_price") * F("quantity")))["total"] or Decimal('0.00')
            this_month_non_project_sales = this_month_solds.filter(project=None).aggregate(
                total=Sum(F("selling_price") * F("quantity")))["total"] or Decimal('0.00')

            year = request.query_params.get('year', None)
            if year:
                yearly_total = filtered_solds.filter(date__year=year).aggregate(
                    total=Sum(F("quantity") * F("selling_price")))['total'] or Decimal('0.00')
            else:
                yearly_total = None

            daily_data = []
            current_date = None
            daily_solds = []

            for sold in filtered_solds:
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
                "this_month_sales_count": this_month_sold_count,
                "this_month_sales": float(this_month_sales),
                "this_month_profit": float(this_month_profit),
                "this_month_project_sales": float(this_month_project_sales),
                "this_month_non_project_sales": float(this_month_non_project_sales),
                "daily_data": daily_data,
            }

            if yearly_total is not None:
                response_data["yearly_total"] = float(yearly_total)

            return Response(response_data)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

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

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")
        project = request.data.get("project")
        customer = request.data.get("customer")
        logistics = request.data.get("logistics")
        sold_item = self.get_object()

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


class ApiCustomer(ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'ceo', 'shopkeeper']
    filter_backends = [SearchFilter]
    search_fields = ['name', 'address']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        all_customers_count = queryset.count()
        active_customers = queryset.filter(project__is_delivered=False).distinct().count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            response_data = {
                "all_customers_count": all_customers_count,
                "active_customers": active_customers,
                "all_customers": data
            }
            return self.get_paginated_response(response_data)

        data = self.get_serializer(queryset, many=True).data
        response_data = {
            "all_customers_count": all_customers_count,
            "active_customers": active_customers,
            "all_customers": data
        }
        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        customer = self.get_object()

        all_projects = customer.project_set.all()
        total_projects_count = all_projects.count()
        active_projects_count = all_projects.filter(is_delivered=False).count()
        total_project_cost = all_projects.annotate(
            paid=ExpressionWrapper(F("selling_price") + F("logistics") + F("service_charge"),
                                   output_field=DecimalField())).aggregate(total=Sum("paid"))["total"] or 0.0

        all_shop_items = customer.sold_set.all()
        total_shop_items_count = all_shop_items.count()

        total_shop_items_cost = all_shop_items.annotate(
            paid=ExpressionWrapper(F("logistics") + (F("selling_price") * F("quantity")),
                                   output_field=DecimalField())).aggregate(total=Sum("paid"))["total"] or 0.0

        data = CustomerDetailSerializer(customer).data

        response_data = {
            "total_projects_count": total_projects_count,
            "active_projects_count": active_projects_count,
            "total_projects_cost": total_project_cost,
            "total_shop_items_count": total_shop_items_count,
            "total_shop_items_cost": total_shop_items_cost,
            "customer_details": data
        }

        return Response(response_data)


class ApiExpenseCategory(ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo']

    def list(self, request, *args, **kwargs):
        """Override list to disable pagination."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ApiExpense(ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()
    filter_class = ExpenseFilter
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo']

    def list(self, request, *args, **kwargs):
        filterset = self.filter_class(request.GET, queryset=self.get_queryset())
        filtered_expenses = filterset.qs.order_by('-date')

        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)

        filtered = filtered_expenses

        # Always calculate totals for the current month
        today = timezone.now().date()
        current_month_total = filtered_expenses.filter(date__month=today.month).aggregate(Sum('amount'))[
                                  'amount__sum'] or 0.0
        current_month_project_total = \
        filtered_expenses.filter(project__isnull=False, date__month=today.month).aggregate(Sum('amount'))[
            'amount__sum'] or 0.0
        current_month_shop_total = \
        filtered_expenses.filter(shop__isnull=False, date__month=today.month).aggregate(Sum('amount'))[
            'amount__sum'] or 0.0

        if year and not month:
            data = []
            for m in range(1, 13):
                monthly_expenses = filtered_expenses.filter(date__year=year, date__month=m)
                total_for_the_month = monthly_expenses.aggregate(Sum('amount'))['amount__sum'] or 0.0

                # Only include months with data
                if monthly_expenses.exists():
                    entries = []
                    for expense in monthly_expenses:
                        entries.append(ExpenseSerializer(expense, context={'request': request}).data)

                    data.append({
                        "month": f"{year}-{m:02d}",
                        "entries": entries,
                        "total_for_the_month": total_for_the_month,
                    })

            yearly_total = filtered_expenses.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0

            response_data = {
                "monthly_total": float(current_month_total),
                "monthly_project_expenses_total": float(current_month_project_total),
                "monthly_shop_expenses_total": float(current_month_shop_total),
                "daily_data": data,
                "yearly_total": float(yearly_total),
            }
            return Response(response_data)

        if year is None and month is None:
            filtered = filtered_expenses.filter(date__year=today.year, date__month=today.month)
        if year is None and month is not None:
            filtered = filtered_expenses.filter(date__year=today.year, date__month=month)

        daily_data = []
        current_date = None
        daily_expenses = []

        for expense in filtered:
            expense_date = expense.date

            if expense_date != current_date:
                if daily_expenses:
                    daily_data.append({
                        "date": current_date,
                        "entries": ExpenseSerializer(daily_expenses, many=True, context={'request': request}).data,
                        "daily_total": sum(e.amount for e in daily_expenses),
                    })
                current_date = expense_date
                daily_expenses = [expense]
            else:
                daily_expenses.append(expense)

        if daily_expenses:
            daily_data.append({
                "date": current_date,
                "entries": ExpenseSerializer(daily_expenses, many=True, context={'request': request}).data,
                "daily_total": sum(e.amount for e in daily_expenses),
            })

        response_data = {
            "monthly_total": float(current_month_total),
            "monthly_project_expenses_total": float(current_month_project_total),
            "monthly_shop_expenses_total": float(current_month_shop_total),
            "daily_data": daily_data,
        }

        if year:
            yearly_total = filtered_expenses.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0
            response_data["yearly_total"] = float(yearly_total)

        return Response(response_data)


class ApiQuotation(ModelViewSet):
    serializer_class = QuotationSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'factory_manager', 'project_manager', 'ceo']


    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return Quotation.objects.filter(product=product_id)

    def create(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data)


class ApiRawMaterialUsed(ReadOnlyModelViewSet):
    serializer_class = RawMaterialUsedSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'factory_manager', 'project_manager', 'ceo']

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return (
            Removed.objects.filter(product=product_id)
            .values("material", "material__name")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("-date")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        # Rename material__name to material_name in the response
        data = [{"material": item["material"], "material_name": item["material__name"], "total_quantity": item["total_quantity"]} for item in serializer.data]
        return Response(data)


class ApiProductContractor(ModelViewSet):
    serializer_class = ProductContractorSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'factory_manager', 'project_manager', 'admin', 'ceo']

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return ProductContractor.objects.filter(product=product_id)

    def create(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contractor = serializer.validated_data.get("contractor")
        cost = serializer.validated_data.get("cost")
        try:
            instance = ProductContractor.objects.get(product=product, contractor=contractor)
            instance.cost = cost
            instance.save()
            serializer = self.get_serializer(instance)
            status_code = status.HTTP_200_OK
        except ProductContractor.DoesNotExist:
            instance = serializer.save(product=product)
            status_code = status.HTTP_201_CREATED
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code, headers=headers)

    def update(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data)


class ApiProductSalaryWorker(ModelViewSet):
    serializer_class = ProductSalaryWorkerSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'project_manager', 'factory_manager', 'ceo']

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return ProductSalaryWorker.objects.filter(product=product_id)

    def create(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        salary_worker = serializer.validated_data.get("salary_worker")
        cost = serializer.validated_data.get("cost")
        try:
            instance = ProductSalaryWorker.objects.get(product=product, salary_worker=salary_worker)
            instance.cost = cost
            instance.save()
            serializer = self.get_serializer(instance)
            status_code = status.HTTP_200_OK
        except ProductSalaryWorker.DoesNotExist:
            instance = serializer.save(product=product)
            status_code = status.HTTP_201_CREATED
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code, headers=headers)

    def update(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data)


class ApiProduct(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.prefetch_related("productcontractor_set", "productsalaryworker_set")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['project__name', 'name']
    ordering = ['progress']
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'shopkeeper', 'factory_manager', 'project_manager','ceo']


class ApiProject(ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all().order_by("start_date")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ['customer__name', 'name']
    ordering = ['progress', "deadline"]
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'ceo', 'shopkeeper', 'admin']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.annotate(computed_progress=Cast(Round(Avg('product__progress')), output_field=IntegerField()))
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        get_all = self.get_queryset()
        all_time_projects_count = get_all.count()
        all_projects_count = get_all.filter(is_delivered=False, archived=False).count()
        completed_projects_count = get_all.filter(computed_progress=100, is_delivered=False, archived=False).count()
        ongoing_projects_count = get_all.filter(computed_progress__lt=100).count()
        average_progress = get_all.filter(is_delivered=False, archived=False).aggregate(avg_progress=Avg("computed_progress"))["avg_progress"] or 0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = {
                "count": self.paginator.page.paginator.count,
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "all_time_projects_count": all_time_projects_count,
                "all_projects_count": all_projects_count,
                "completed_projects_count": completed_projects_count,
                "ongoing_projects_count": ongoing_projects_count,
                "average_progress": round(average_progress, 2),
                "all_projects": serializer.data,
            }
            return Response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            "count": queryset.count(),
            "next": None,
            "previous": None,
            "all_time_projects_count": all_time_projects_count,
            "all_ongoing_projects_count": all_projects_count,
            "completed_projects_count": completed_projects_count,
            "ongoing_projects_count": ongoing_projects_count,
            "average_progress": round(average_progress, 2),
            "all_projects": serializer.data,
        }
        return Response(response_data)


class ApiRawMaterial(ModelViewSet):
    serializer_class = RawMaterialSerializer
    queryset = RawMaterial.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = RawMaterialFilter
    search_fields = ['name', 'description']
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'ceo']

    def get_queryset(self):
        qs = super().get_queryset()
        if 'archived' not in self.request.query_params:
            qs = qs.filter(archived=False)
        return qs

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            AddRawMaterials.objects.create(item=instance, quantity=instance.quantity, cost_price=instance.price,
                                           name=instance.name)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        total_store_count = queryset.count()
        total_store_value = queryset.aggregate(
            total_value=Coalesce(Sum(F('quantity') * F('price')), 0.0, output_field=DecimalField()))['total_value'] or 0.0

        page = self.paginate_queryset(queryset)
        if page is not None:
            serialized_items = self.get_serializer(page, many=True).data
        else:
            serialized_items = self.get_serializer(queryset, many=True).data

        response_data = {
            "total_store_count": total_store_count,
            "total_stock_value": float(total_store_value),
            "items": serialized_items,
        }

        if page is not None:
            return self.get_paginated_response(response_data)
        return Response(response_data)


class ApiRemoved(ModelViewSet):
    serializer_class = RemovedSerializer
    queryset = Removed.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = RemovedFilter
    search_fields = ['material__name', 'product__name', 'material__description']
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'ceo']

    def list(self, request, *args, **kwargs):
        today = timezone.now().date()
        queryset = self.get_queryset()
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_removed = filterset.qs.order_by('-date')

        this_month_removed_count = queryset.filter(date__month=today.month).count()
        this_month_removed = queryset.filter(date__month=today.month).aggregate(total=Sum(F("price") * F("quantity")))[
            "total"]

        # filters
        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)
        day = request.query_params.get('day', None)

        filtered = filtered_removed

        if day is not None and year is None and month is None:
            year = today.year
            month = today.month

        if year is None and month is None:
            year = today.year
            month = today.month

        if year is not None and month is None and day is None:
            filtered = filtered_removed.filter(date__year=year)

        elif year is not None and day is not None:
            if month is None:
                month = today.month
            filtered = filtered_removed.filter(date__year=year, date__month=month, date__day=day)

        elif year is not None and month is not None and day is None:
            filtered = filtered_removed.filter(date__year=year, date__month=month)

        elif year is not None and month is not None and day is not None:
            filtered = filtered_removed.filter(date__year=year, date__month=month, date__day=day)

        daily_data = []
        current_date = None
        daily_removed = []
        for removed in filtered:
            removed_date = removed.date.date() if isinstance(removed.date, datetime) else removed.date

            if current_date != removed_date:
                if daily_removed:
                    daily_data.append({
                        "date": current_date,
                        "entries": self.get_serializer(daily_removed, many=True).data,
                        "daily_total": sum(s.price * s.quantity for s in daily_removed)
                    })
                current_date = removed_date
                daily_removed = [removed]
            else:
                daily_removed.append(removed)
        if daily_removed:
            daily_data.append({
                "date": current_date,
                "entries": self.get_serializer(daily_removed, many=True).data,
                "daily_total": sum(s.price * s.quantity for s in daily_removed)
            })
        response_data = {
            "this_month_removed_count": this_month_removed_count,
            "this_month_removed": this_month_removed,
            "daily_data": daily_data,
        }
        if year:
            yearly_total = queryset.filter(date__year=year).aggregate(total=Sum(F("quantity") * F("price")))[
                               'total'] or 0.0
            response_data["yearly_total"] = yearly_total
        return Response(response_data)

    def create(self, request, *args, **kwargs):
        material = request.data.get("material")
        quantity = request.data.get("quantity")
        product = request.data.get("product")

        if not material or not quantity or not product:
            return Response(
                {"error": "'material', 'quantity' and 'product' are all required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = Decimal(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"error": "'quantity' must be a valid decimal number."}, status=status.HTTP_400_BAD_REQUEST)

        material_data = get_object_or_404(RawMaterial, id=material)
        product_data = get_object_or_404(Product, id=product)
        if quantity > material_data.quantity:
            return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)

        Removed.objects.create(material=material_data, quantity=quantity, product=product_data,
                               price=material_data.price, name=material_data.name)
        material_data.quantity -= quantity
        material_data.save()

        return Response(
            {"message": "Sale completed successfully."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        removed_item = self.get_object()
        if removed_item.material is not None:
            material_data = get_object_or_404(RawMaterial, id=removed_item.material.id)
            material_data.quantity += removed_item.quantity
            material_data.save()
            removed_item.delete()
            return Response({"message": "Removed Material deleted successfully and raw material updated successfully."},
                            status=204)

        removed_item.delete()
        return Response({
                            "message": "Removed Material deleted but raw material not updated because it has been deleted already. try creating a new one manually."},
                        status=204)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        material = request.data.get("material")
        quantity = request.data.get("quantity")
        product = request.data.get("product")
        removed_item = self.get_object()

        if not material and not quantity and not product:
            return Response(
                {"error": "Either one of 'material', 'quantity', 'product' or more is required."},
                status=status.HTTP_400_BAD_REQUEST)

        if quantity is not None:
            try:
                quantity = Decimal(quantity)
                if quantity <= 0:
                    return Response({"error": "Quantity must be a positive number."},
                                    status=status.HTTP_400_BAD_REQUEST)
            except (InvalidOperation, TypeError):
                return Response({"error": "quantity must be a valid decimal number (e.g., 2.3, 0.5)"},
                                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if material and int(material) != int(removed_item.material.id):
                old_raw_material_item = get_object_or_404(RawMaterial, id=removed_item.material.id)
                old_raw_material_item.quantity += removed_item.quantity

                new_raw_material_item = get_object_or_404(RawMaterial, id=material)

                if quantity is None:
                    quantity = removed_item.quantity
                if quantity > new_raw_material_item.quantity:
                    return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)

                old_raw_material_item.save()
                new_raw_material_item.quantity -= quantity
                new_raw_material_item.save()

                removed_item.material = new_raw_material_item
                removed_item.quantity = quantity
                removed_item.price = new_raw_material_item.price
                removed_item.name = new_raw_material_item.name
                removed_item.save()

                return Response({"message": "removed raw material edited successfully."}, status=status.HTTP_200_OK)

            if quantity is not None and quantity != removed_item.quantity:
                raw_material_item = get_object_or_404(RawMaterial, id=removed_item.material.id)
                difference = abs(quantity - removed_item.quantity)

                if quantity > removed_item.quantity:
                    if difference > raw_material_item.quantity:
                        return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)
                    raw_material_item.quantity -= difference
                else:
                    raw_material_item.quantity += difference

                raw_material_item.save()
                removed_item.quantity = quantity
                removed_item.save()

                return Response({"message": "removed raw material quantity edited successfully."},
                                status=status.HTTP_200_OK)

            return Response({"message": "No changes made."}, status=status.HTTP_200_OK)


class ApiContractors(ModelViewSet):
    serializer_class = ContractorsSerializer
    queryset = Contractors.objects.all()
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'factory_manager', 'project_manager', 'admin', 'ceo']
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_still_active']
    search_fields = ['first_name', 'last_name', 'email']

    def list(self, request, *args, **kwargs):
        try:
            today = timezone.now().date()
            start_of_week = today - timezone.timedelta(days=today.weekday())

            filtered_contractors = self.filter_queryset(self.get_queryset())

            all_contractors_count = filtered_contractors.count()
            all_active_contractors_count = filtered_contractors.filter(is_still_active=True).count()
            total_contractors_monthly_pay = filtered_contractors.filter(
                paid__date__month=today.month
            ).aggregate(total=Sum("paid__amount"))["total"] or 0.0
            total_contractors_weekly_pay = filtered_contractors.filter(
                paid__date__range=(start_of_week, today)
            ).aggregate(total=Sum("paid__amount"))["total"] or 0.0

            page = self.paginate_queryset(filtered_contractors)
            if page is not None:
                data = self.serializer_class(page, many=True, context={'request': request}).data
                response_data = {
                    "all_contractors_count": all_contractors_count,
                    "all_active_contractors_count": all_active_contractors_count,
                    "total_contractors_monthly_pay": float(total_contractors_monthly_pay),
                    "total_contractors_weekly_pay": float(total_contractors_weekly_pay),
                    "contractor": data,
                }
                return self.get_paginated_response(response_data)

            data = self.serializer_class(filtered_contractors, many=True, context={'request': request}).data
            response_data = {
                "all_contractors_count": all_contractors_count,
                "all_active_contractors_count": all_active_contractors_count,
                "total_contractors_monthly_pay": float(total_contractors_monthly_pay),
                "total_contractors_weekly_pay": float(total_contractors_weekly_pay),
                "contractor": data,
            }

            return Response(response_data)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class ApiSalaryWorkers(viewsets.ModelViewSet):
    serializer_class = SalaryWorkersSerializer
    queryset = SalaryWorkers.objects.all()
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'factory_manager', 'ceo']
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_still_active']
    search_fields = ['first_name', 'last_name', 'email']

    def list(self, request, *args, **kwargs):
        try:
            today = timezone.now().date()
            start_of_week = today - timezone.timedelta(days=today.weekday())

            filtered_salary_workers = self.filter_queryset(self.get_queryset())

            salary_workers_count = filtered_salary_workers.count()
            active_salary_workers_count = filtered_salary_workers.filter(is_still_active=True).count()
            total_salary_workers_monthly_pay = filtered_salary_workers.aggregate(
                total=Sum("salary")
            )["total"] or 0.0
            total_paid = filtered_salary_workers.filter(
                paid__date__month=today.month
            ).aggregate(total=Sum("paid__amount"))["total"] or 0.0

            page = self.paginate_queryset(filtered_salary_workers)
            if page is not None:
                data = self.serializer_class(page, many=True, context={'request': request}).data
                response_data = {
                    "salary_workers_count": salary_workers_count,
                    "active_salary_workers_count": active_salary_workers_count,
                    "total_salary_workers_monthly_pay": float(total_salary_workers_monthly_pay),
                    "total_paid": float(total_paid),
                    "workers": data,
                }
                return self.get_paginated_response(response_data)

            data = self.serializer_class(filtered_salary_workers, many=True, context={'request': request}).data
            response_data = {
                "salary_workers_count": salary_workers_count,
                "active_salary_workers_count": active_salary_workers_count,
                "total_salary_workers_monthly_pay": float(total_salary_workers_monthly_pay),
                "total_paid": float(total_paid),
                "workers": data,
            }

            return Response(response_data)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class ApiSalaryWorkersRecord(ModelViewSet):
    serializer_class = SalaryWorkersRecordSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'factory_manager', 'ceo']


    def get_queryset(self):
        salary_id = self.kwargs.get('salary_worker_pk')
        return SalaryWorkersRecord.objects.filter(salary_worker=salary_id)

    def perform_create(self, serializer):
        salary_id = self.kwargs.get('salary_worker_pk')
        salary_worker = get_object_or_404(SalaryWorkers, pk=salary_id)
        serializer.save(salary_worker=salary_worker)

    def perform_update(self, serializer):
        salary_id = self.kwargs.get('salary_worker_pk')
        salary_worker = get_object_or_404(SalaryWorkers, pk=salary_id)
        serializer.save(salary_worker=salary_worker)


class ApiContractorRecord(ModelViewSet):
    serializer_class = ContractorRecordSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['admin', 'factory_manager', 'ceo']


    def get_queryset(self):
        contractor_id = self.kwargs.get('contractor_pk')
        return ContractorRecord.objects.filter(contractor=contractor_id)

    def perform_create(self, serializer):
        contractor_id = self.kwargs.get('contractor_pk')
        contractor = get_object_or_404(Contractors, pk=contractor_id)
        serializer.save(contractor=contractor)

    def perform_update(self, serializer):
        contractor_id = self.kwargs.get('contractor_pk')
        contractor = get_object_or_404(Contractors, pk=contractor_id)
        serializer.save(contractor=contractor)


class OverheadCostViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = OverheadCostSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['ceo']


    def get_queryset(self):
        return OverheadCost.objects.all()

    def get_object(self):
        instance, created = OverheadCost.objects.get_or_create(id=1)
        return instance

    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        if request.method.upper() == 'PUT':
            return Response(
                {'detail': 'PUT method is not allowed; only PATCH is permitted.'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        return super().update(request, *args, **kwargs)


class ApiAssets(viewsets.ModelViewSet):
    serializer_class = AssetsSerializer
    queryset = Assets.objects.all().order_by('-is_still_available', '-date_added')
    pagination_class = AssetsPagination
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo']
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_still_available']
    search_fields = ['name']

    def list(self, request, *args, **kwargs):
        filtered_assets = self.filter_queryset(self.get_queryset())

        all_assets_total = filtered_assets.filter(is_still_available=True).aggregate(Sum('value'))['value__sum'] or 0.0
        no_of_good_assets = filtered_assets.filter(is_still_available=True).count()
        no_of_bad_assets = filtered_assets.filter(is_still_available=False).count()
        total_assets_count = filtered_assets.count()

        page = self.paginate_queryset(filtered_assets)
        if page is not None:
            data = self.serializer_class(page, many=True, context={'request': request}).data
            response_data = {
                "total_assets_count": total_assets_count,
                "good_assets_count": no_of_good_assets,
                "good_assets_value": float(all_assets_total),
                "depreciated_assets_count": no_of_bad_assets,
                "assets": data
            }
            return self.get_paginated_response(response_data)

        data = self.serializer_class(filtered_assets, many=True, context={'request': request}).data
        response_data = {
            "total_assets_count": total_assets_count,
            "good_assets_count": no_of_good_assets,
            "good_assets_value": float(all_assets_total),
            "depreciated_assets_count": no_of_bad_assets,
            "assets": data
        }

        return Response(response_data)


class ApiOtherProductionRecord(ModelViewSet):
    serializer_class = OtherProductionSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'ceo']

    def get_queryset(self):
        project_id = self.kwargs.get('project_pk')
        return OtherProduction.objects.filter(project=project_id)

    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_pk')
        project = get_object_or_404(Project, pk=project_id)
        serializer.save(project=project)

    def perform_update(self, serializer):
        project_id = self.kwargs.get('project_pk')
        project = get_object_or_404(Project, pk=project_id)
        serializer.save(project=project)


class ApiPaid(viewsets.ModelViewSet):
    serializer_class = PaidSerializer
    queryset = Paid.objects.all().order_by('-date')
    filterset_class = PaidFilter
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo']

    def list(self, request, *args, **kwargs):
        today = timezone.now().date()
        queryset = self.get_queryset()
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_paid = filterset.qs.order_by('-date')

        monthly_total = filtered_paid.filter(date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0.0
        salary_paid_this_month = filtered_paid.filter(contract=None).aggregate(Sum('amount'))['amount__sum'] or 0.0
        contractors_paid_this_month = filtered_paid.filter(salary=None).aggregate(Sum('amount'))['amount__sum'] or 0.0
        # filters
        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)
        day = request.query_params.get('day', None)

        filtered = filtered_paid

        if day is not None and year is None and month is None:
            year = today.year
            month = today.month

        if year is None and month is None:
            year = today.year
            month = today.month

        if year is not None and month is None and day is None:
            filtered = filtered_paid.filter(date__year=year)

        elif year is not None and day is not None:
            if month is None:
                month = today.month
            filtered = filtered_paid.filter(date__year=year, date__month=month, date__day=day)

        elif year is not None and month is not None and day is None:
            filtered = filtered_paid.filter(date__year=year, date__month=month)

        elif year is not None and month is not None and day is not None:
            filtered = filtered_paid.filter(date__year=year, date__month=month, date__day=day)

        daily_data = []
        current_date = None
        daily_paid = []
        for paid in filtered:
            paid_date = paid.date.date() if isinstance(paid.date, datetime) else paid.date

            if current_date != paid_date:
                if daily_paid:
                    daily_data.append({
                        "date": current_date,
                        "entries": self.get_serializer(daily_paid, many=True).data,
                        "daily_total": sum(s.amount for s in daily_paid)
                    })
                current_date = paid_date
                daily_paid = [paid]
            else:
                daily_paid.append(paid)
        if daily_paid:
            daily_data.append({
                "date": current_date,
                "entries": self.get_serializer(daily_paid, many=True).data,
                "daily_total": sum(s.amount for s in daily_paid)
            })
        response_data = {
            "monthly_total": monthly_total,
            "salary_paid_this_month": salary_paid_this_month,
            "contractors_paid_this_month": contractors_paid_this_month,
            "daily_data": daily_data,
        }
        if year:
            yearly_total = queryset.filter(date__year=year).aggregate(total=Sum("amount"))['total'] or 0.0
            response_data["yearly_total"] = yearly_total
        return Response(response_data)


class StoreQuotation(ModelViewSet):
    serializer_class = QuotationSerializer
    queryset = Quotation.objects.filter(product__progress__lt=100).order_by('-product__project__start_date')
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['product__project__name', 'product__name', 'product__production_note']
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'ceo']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        total_quotation_count = queryset.count()
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            "total_quotation_count": total_quotation_count,
            "quotation": serializer.data
        }
        return Response(response_data)