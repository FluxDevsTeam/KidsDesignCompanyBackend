from django.db import transaction
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone

from .pagination import AssetsPagination
from .permissions import IsCEO, IsArtisan, IsStoreKeeper, IsProjectManager, IsOwnerOrAdmin, IsAdminOrReadOnly, \
    IsArtisanReadOnly, IsStoreKeeperReadonly, IsManager
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
from .filters import ExpenseFilter, InventoryItemFilter, AddStockFilter, SoldFilter, ProjectFilter, \
    AddRawMaterialsFilter, PaidFilter
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from django.db.models import F, ExpressionWrapper, DecimalField, Sum
from django.db.models import Avg, IntegerField
from django.db.models.functions import Round, Cast, Coalesce

User = get_user_model()


class ApiInventoryItem(ModelViewSet):
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = InventoryItemFilter
    search_fields = ['name', 'description']
    pagination_class = PageNumberPagination

    def get_queryset(self):
        qs = super().get_queryset()
        if 'archived' not in self.request.query_params:
            qs = qs.filter(archived=False)
        return qs

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            AddStock.objects.create(
                item=instance,
                name=instance.name,
                cost_price=instance.cost_price,
                quantity=instance.stock
            )

    def list(self, request, *args, **kwargs):
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_items = filterset.qs
        total_stock_count = filtered_items.count()
        total_stock_value = filtered_items.aggregate(
            total_stock_value=Coalesce(Sum(F('stock') * F('selling_price')), 0.0, output_field=DecimalField())
        )['total_stock_value'] or 0.0

        total_cost_value = filtered_items.aggregate(
            total_cost_value=Coalesce(Sum(F('stock') * F('cost_price')), 0.0, output_field=DecimalField())
        )['total_cost_value'] or 0.0

        total_profit = total_stock_value - total_cost_value



        page = self.paginate_queryset(filtered_items)
        if page is not None:
            serialized_items = self.get_serializer(page, many=True).data
        else:
            serialized_items = self.get_serializer(filtered_items, many=True).data

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

    def list(self, request, *args, **kwargs):
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_raw_materials = filterset.qs.order_by('-date')

        # Group by day
        daily_data = []
        current_date = None
        daily_entries = []

        for entry in filtered_raw_materials:
            entry_date = entry.date.date()

            if entry_date != current_date:
                if daily_entries:
                    daily_data.append({
                        "date": current_date.strftime('%Y-%m-%d'),
                        "entries": AddRawMaterialsSerializer(daily_entries, many=True).data,
                        "daily_total": sum(float(e.quantity) for e in daily_entries),
                    })
                current_date = entry_date
                daily_entries = [entry]
            else:
                daily_entries.append(entry)

        if daily_entries:
            daily_data.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "entries": AddRawMaterialsSerializer(daily_entries, many=True).data,
                "daily_total": sum(float(e.quantity) for e in daily_entries),
            })

        # Totals
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())

        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)

        if year and not month:
            monthly_data = []
            for m in range(1, 13):
                monthly_entries = filtered_raw_materials.filter(date__year=year, date__month=m)
                total_for_the_month = monthly_entries.aggregate(Sum('quantity'))['quantity__sum'] or 0.0

                if monthly_entries.exists():
                    entries = []
                    for entry in monthly_entries:
                        entries.append(AddRawMaterialsSerializer(entry).data)

                    monthly_data.append({
                        "month": f"{year}-{m:02d}",
                        "entries": entries,
                        "total_for_the_month": float(total_for_the_month),
                    })

            yearly_total = filtered_raw_materials.filter(date__year=year).aggregate(Sum('quantity'))['quantity__sum'] or 0.0

            response_data = {
                "monthly_total": filtered_raw_materials.filter(date__month=today.month).aggregate(Sum('quantity'))['quantity__sum'] or 0.0,
                "weekly_total": filtered_raw_materials.filter(date__range=[start_of_week, today]).aggregate(Sum('quantity'))['quantity__sum'] or 0.0,
                "daily_data": daily_data,
                "monthly_data": monthly_data,
                "yearly_total": float(yearly_total),
            }
        else:
            if year and month:
                monthly_total = filtered_raw_materials.filter(date__year=year, date__month=month).aggregate(Sum('quantity'))['quantity__sum'] or 0.0
            else:
                monthly_total = filtered_raw_materials.filter(date__month=today.month).aggregate(Sum('quantity'))['quantity__sum'] or 0.0

            response_data = {
                "monthly_total": float(monthly_total),
                "weekly_total": filtered_raw_materials.filter(date__range=[start_of_week, today]).aggregate(Sum('quantity'))['quantity__sum'] or 0.0,
                "daily_data": daily_data,
            }

            if year:
                yearly_total = filtered_raw_materials.filter(date__year=year).aggregate(Sum('quantity'))['quantity__sum'] or 0.0
                response_data["yearly_total"] = float(yearly_total)

        return Response(response_data)


class ApiAddStock(ModelViewSet):
    serializer_class = AddSockSerializer
    queryset = AddStock.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AddStockFilter
    search_fields = ["item__name"]
    # permission_classes = [IsCEO | IsStoreKeeper | IsManager]

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
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_stock = filterset.qs.order_by('-date')

        # Group by day
        daily_data = []
        current_date = None
        daily_entries = []

        for entry in filtered_stock:
            entry_date = entry.date

            if entry_date != current_date:
                if daily_entries:
                    daily_data.append({
                        "date": current_date,
                        "entries": AddSockSerializer(daily_entries, many=True).data,
                        "daily_total": sum(e.quantity for e in daily_entries),
                    })
                current_date = entry_date
                daily_entries = [entry]
            else:
                daily_entries.append(entry)

        if daily_entries:
            daily_data.append({
                "date": current_date,
                "entries": AddSockSerializer(daily_entries, many=True).data,
                "daily_total": sum(e.quantity for e in daily_entries),
            })

        # Totals
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())

        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)

        if year and month:
            monthly_total = filtered_stock.filter(date__year=year, date__month=month).aggregate(Sum('quantity'))['quantity__sum'] or 0.0
        else:
            monthly_total = filtered_stock.filter(date__month=today.month).aggregate(Sum('quantity'))['quantity__sum'] or 0.0

        weekly_total = filtered_stock.filter(date__range=[start_of_week, today]).aggregate(Sum('quantity'))['quantity__sum'] or 0.0

        response_data = {
            "monthly_total": monthly_total,
            "weekly_total": weekly_total,
            "daily_data": daily_data,
        }

        if year:
            yearly_total = filtered_stock.filter(date__year=year).aggregate(Sum('quantity'))['quantity__sum'] or 0.0
            response_data["yearly_total"] = yearly_total

        return Response(response_data)


class ApiInventoryCategory(ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    # permission_classes = [IsCEO | IsProjectManager]


class ApiStoreCategory(ModelViewSet):
    queryset = StoreCategory.objects.all()
    serializer_class = StoreCategorySerializer
    # permission_classes = [IsCEO | IsProjectManager]


class ApiSold(ModelViewSet):
    serializer_class = SoldSerializer
    queryset = Sold.objects.all()
    # permission_classes = [IsCEO | IsStoreKeeper]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = SoldFilter
    search_fields = ['item__name', 'customer__name']

    def list(self, request, *args, **kwargs):
        today = timezone.now().date()

        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_solds = filterset.qs.order_by('-date')

        this_month_sold_count = filtered_solds.filter(date__month=today.month).count()
        this_month_sales = filtered_solds.filter(date__month=today.month).aggregate(total=Sum(F("selling_price")* F("quantity")))["total"]
        this_month_profit = filtered_solds.filter(date__month=today.month).aggregate(total=Sum((F("selling_price")* F("quantity") - (F("cost_price") * F("quantity"))), output_field=DecimalField(max_digits=10, decimal_places=2)))["total"]

        this_month_project_sales = filtered_solds.filter(date__month=today.month, logistics=None).aggregate(total=Sum(F("selling_price") * F("quantity")))["total"]
        this_month_non_project_sales = filtered_solds.filter(date__month=today.month, project=None).aggregate(total=Sum(F("selling_price") * F("quantity")))["total"]

        # filters
        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)
        day = request.query_params.get('day', None)

        if not month and not year and not day:
            filtered = filtered_solds.filter(date__month=today.month)
        if month and not year and not day:
            filtered = filtered_solds.filter(date__month=today.month)

        daily_data = []
        current_date = None
        daily_solds = []
        for sold in filtered:
            sold_date = sold.date.date() if isinstance(sold.date, datetime) else sold.date
            if current_date != sold_date:
                if daily_solds:
                    daily_data.append({
                        "date": current_date.strftime('%Y-%m-%d'),
                        "entries": self.get_serializer(daily_solds, many=True).data,
                        "daily_total": sum(s.total_price for s in daily_solds)
                    })
                current_date = sold_date
                daily_solds = [sold]
            else:
                daily_solds.append(sold)
        if daily_solds:
            daily_data.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "entries": self.get_serializer(daily_solds, many=True).data,
                "daily_total": sum(s.total_price for s in daily_solds)
            })
        total_price_expr = ExpressionWrapper(F('quantity') * F('selling_price'), output_field=DecimalField(max_digits=10, decimal_places=2))

        response_data = {
            "this_month_sales_count": this_month_sold_count,
            "this_month_sales": this_month_sales,
            "this_month_profit": this_month_profit,
            "this_month_project_sales": this_month_project_sales,
            "this_month_non_project_sales": this_month_non_project_sales,
            "daily_data": daily_data,
        }
        if year:
            yearly_total = self.get_queryset().filter(date__year=year).aggregate(total=Sum(total_price_expr))['total'] or 0.0
            response_data["yearly_total"] = yearly_total
            response_data.pop("monthly_total")
        return Response(response_data)

    def create(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")
        customer = request.data.get("customer")
        project = request.data.get("project")
        logistics = request.data.get("logistics")

        if bool(customer) == bool(project):
            if not customer:
                return Response({"error": "Either 'customer' or 'project' is required."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "Only one of 'customer' or 'project' is allowed."}, status=status.HTTP_400_BAD_REQUEST)

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
            Sold.objects.create(item=inventory_item, quantity=quantity, customer=customer, cost_price=inventory_item.cost_price, selling_price=inventory_item.selling_price, project=project_instance, name=inventory_item.name)
        else:
            customer_data = get_object_or_404(Customer, id=customer)
            Sold.objects.create(item=inventory_item, quantity=quantity, customer=customer_data, cost_price=inventory_item.cost_price, selling_price=inventory_item.selling_price, logistics=logistics, name=inventory_item.name)

        inventory_item.stock -= quantity
        inventory_item.save()
        return Response(
            {"message": "Sale completed successfully."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        sold_item = self.get_object()
        if sold_item.item is not None:
            inventory_item = get_object_or_404(InventoryItem, pk=sold_item.item.id)
            inventory_item.stock += sold_item.quantity
            inventory_item.save()
            sold_item.delete()
            return Response({"message": "Sold item deleted and inventory updated."}, status=204)

        sold_item.delete()
        return Response({"message": "Sold item deleted but inventory not updated because item has beed deleted. you can create an invcentory again and add it manually."}, status=204)


    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")
        project = request.data.get("project")
        customer = request.data.get("customer")
        logistics = request.data.get("logistics")
        sold_item = self.get_object()

        if (customer and (not logistics)) and (logistics and (not customer)) and (customer and (not sold_item.logistics)) and (logistics and (not sold_item.customer)):
            return Response(
                {"error": "both 'customer' and 'logistics' is required."}, status=status.HTTP_400_BAD_REQUEST)

        if (((project and logistics) or (project and sold_item.logistics) or (sold_item.project and logistics)) and (not customer) and project) and (project and (logistics or customer)):
            return Response(
                {"error": "you cant set logistics for item sold in a project"}, status=status.HTTP_400_BAD_REQUEST)

        if customer and project:
            return Response(
                {"error": "only one of either 'customer' or 'project' is required."}, status=status.HTTP_400_BAD_REQUEST)
        if project:
            project_db = get_object_or_404(Project, id=int(project))
            project = project_db

        if customer:
            customer_db = get_object_or_404(Customer, id=int(customer))
            customer = customer_db

        if all(field is None for field in [item_id, quantity, project, customer, logistics]):
            return Response(
                {"error": "At least one of 'item', 'quantity', 'cost_price', 'selling_price', 'customer', 'logistics' or 'project' is required."}, status=status.HTTP_400_BAD_REQUEST)

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

                return Response({"data": f"{', '.join(updated_fields)} updated successfully"}, status=status.HTTP_200_OK)

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

                return Response({"data": f"{', '.join(updated_fields)} updated successfully"}, status=status.HTTP_200_OK)
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
                return Response({"data": f"{', '.join(updated_fields)} updated successfully"}, status=status.HTTP_200_OK)

            return Response({"message": "No changes made."}, status=status.HTTP_200_OK)


class ApiCustomer(ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()

    def list(self, request, *args, **kwargs):
        all_customers = self.get_queryset()
        all_customers_count = all_customers.count()
        active_customers = all_customers.filter(project__is_delivered=False).distinct().count()

        page = self.paginate_queryset(all_customers)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            response_data = {
                "all_customers_count": all_customers_count,
                "active_customers": active_customers,
                "all_customers": data
            }
            return self.get_paginated_response(response_data)

        data = self.get_serializer(all_customers, many=True).data
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
        total_project_cost = all_projects.annotate(paid=ExpressionWrapper(F("selling_price") + F("logistics") + F("service_charge"),output_field=DecimalField())).aggregate(total=Sum("paid"))["total"] or 0.0

        all_shop_items = customer.sold_set.all()
        total_shop_items_count = all_shop_items.count()

        total_shop_items_cost = all_shop_items.annotate(paid=ExpressionWrapper(F("logistics") + (F("selling_price") * F("quantity")),output_field=DecimalField())).aggregate(total=Sum("paid"))["total"] or 0.0

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
    # permission_classes = [IsCEO | IsProjectManager]


class ApiExpense(ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()
    filter_class = ExpenseFilter

    # permission_classes = [IsCEO | IsProjectManager]

    def list(self, request, *args, **kwargs):
        filterset = self.filter_class(request.GET, queryset=self.get_queryset())
        filtered_expenses = filterset.qs.order_by('-date')

        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)

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
            monthly_data = []
            for m in range(1, 13):
                monthly_expenses = filtered_expenses.filter(date__year=year, date__month=m)
                total_for_the_month = monthly_expenses.aggregate(Sum('amount'))['amount__sum'] or 0.0

                # Only include months with data
                if monthly_expenses.exists():
                    entries = []
                    for expense in monthly_expenses:
                        entries.append(ExpenseSerializer(expense).data)

                    monthly_data.append({
                        "month": f"{year}-{m:02d}",
                        "entries": entries,
                        "total_for_the_month": total_for_the_month,
                    })

            yearly_total = filtered_expenses.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0

            response_data = {
                "monthly_total": current_month_total,
                "monthly_project_expenses_total": current_month_project_total,
                "monthly_shop_expenses_total": current_month_shop_total,
                "monthly_data": monthly_data,
                "yearly_total": yearly_total,
            }
            return Response(response_data)

        daily_data = []
        current_date = None
        daily_expenses = []

        for expense in filtered_expenses:
            expense_date = expense.date.date()

            if expense_date != current_date:
                if daily_expenses:
                    daily_data.append({
                        "date": current_date.strftime('%Y-%m-%d'),
                        "entries": ExpenseSerializer(daily_expenses, many=True).data,
                        "daily_total": sum(e.amount for e in daily_expenses),
                    })
                current_date = expense_date
                daily_expenses = [expense]
            else:
                daily_expenses.append(expense)

        if daily_expenses:
            daily_data.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "entries": ExpenseSerializer(daily_expenses, many=True).data,
                "daily_total": sum(e.amount for e in daily_expenses),
            })

        start_of_week = today - timedelta(days=today.weekday())
        weekly_total = filtered_expenses.filter(date__date__range=[start_of_week, today]).aggregate(Sum('amount'))[
                           'amount__sum'] or 0.0

        response_data = {
            "monthly_total": current_month_total,
            "monthly_project_expenses_total": current_month_project_total,
            "monthly_shop_expenses_total": current_month_shop_total,
            "weekly_total": weekly_total,
            "daily_data": daily_data,
        }

        if year:
            yearly_total = filtered_expenses.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0
            response_data["yearly_total"] = yearly_total

        return Response(response_data)


class ApiQuotation(ModelViewSet):
    serializer_class = QuotationSerializer

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

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return Removed.objects.filter(product=product_id)
    # permission_classes = [IsCEO | IsProjectManager | IsStoreKeeperReadonly]


class ApiProductContractor(ModelViewSet):
    serializer_class = ProductContractorSerializer

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

    # permission_classes = [IsCEO | IsProjectManager | IsStoreKeeperReadonly]

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return ProductSalaryWorker.objects.filter(product=product_id)

    def create(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contractor = serializer.validated_data.get("contractor")
        cost = serializer.validated_data.get("cost")
        try:
            instance = ProductSalaryWorker.objects.get(product=product, contractor=contractor)
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
    # permission_classes = [IsCEO | IsProjectManager]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['project__name', 'name']
    ordering = ['progress']


class ApiProject(ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    # permission_classes = [IsCEO | IsProjectManager]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ['customer__name', 'name']
    ordering = ['progress', "deadline"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.annotate(computed_progress=Cast(Round(Avg('product__progress')), output_field=IntegerField()))
        return qs

    def list(self, request, *args, **kwargs):
        projects = self.get_queryset()
        all_projects_count = projects.count()

        page = self.paginate_queryset(projects)
        if page is not None:
            all_projects = self.get_serializer(projects, many=True).data
            response_data = {
                "all_projects_count": all_projects_count,
                "all_projects": all_projects
            }
            return Response(response_data)
        all_projects = self.get_serializer(projects, many=True).data
        response_data = {
            "all_projects_count": all_projects_count,
            "all_projects": all_projects
        }
        return Response(response_data)


class ApiRawMaterial(ModelViewSet):
    serializer_class = RawMaterialSerializer
    queryset = RawMaterial.objects.all()
    # permission_classes = [IsCEO | IsStoreKeeper]

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            AddRawMaterials.objects.create(item=instance, quantity=instance.quantity)


class ApiRemoved(ModelViewSet):
    serializer_class = RemovedSerializer
    queryset = Removed.objects.all()

    # permission_classes = [IsCEO | IsStoreKeeper]

    def create(self, request, *args, **kwargs):
        material = request.data.get("material")
        quantity = request.data.get("quantity")
        product = request.data.get("product")

        if not material or not quantity or not product:
            return Response(
                {"error": "'material' and 'product' are all required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            return Response(
                {"error": "'quantity' must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        material_data = get_object_or_404(RawMaterial, id=material)
        product_data = get_object_or_404(Product, id=product)
        if quantity > material_data.quantity:
            return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)

        Removed.objects.create(material=material_data, quantity=quantity, product=product_data, price=material_data.price)
        material_data.quantity -= quantity
        material_data.save()

        return Response(
            {"message": "Sale completed successfully."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        removed_item = self.get_object()
        material_data = get_object_or_404(RawMaterial, id=removed_item.material)
        material_data.quantity += removed_item.quantity
        material_data.save()
        removed_item.delete()

        return Response({"message": "Removed Material deleted successfully."}, status=204)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        material = request.data.get("material")
        quantity = request.data.get("quantity")
        product = request.data.get("product")
        removed_item = self.get_object()

        if not material and not quantity and not product:
            return Response(
                {"error": "Either one of 'material', 'quantity', 'product' or more is required."}, status=status.HTTP_400_BAD_REQUEST)

        if quantity is not None:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    return Response({"error": "Quantity must be a positive number."},
                                    status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "quantity most be an number"}, status=status.HTTP_400_BAD_REQUEST)

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

                removed_item.material.id = material
                removed_item.quantity = quantity
                removed_item.price = new_raw_material_item.price
                removed_item.save()

                return Response({"message": "removed raw material edited successfully."}, status=status.HTTP_200_OK)

            if quantity is not None and quantity != removed_item.quantity:
                raw_material_item = get_object_or_404(RawMaterial, id=removed_item.quantity.id)
                difference = abs(quantity - removed_item.quantity)

                if quantity > removed_item.quantity:
                    if difference > raw_material_item.quantity:
                        return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)
                    raw_material_item.stock -= difference
                else:
                    raw_material_item.stock += difference

                raw_material_item.save()
                removed_item.quantity = quantity
                removed_item.save()

                return Response({"message": "removed raw material quantity edited successfully."}, status=status.HTTP_200_OK)

            return Response({"message": "No changes made."}, status=status.HTTP_200_OK)


class ApiContractors(ModelViewSet):
    serializer_class = ContractorsSerializer
    queryset = Contractors.objects.all()
    # permission_classes = [IsCEO | IsArtisanReadOnly | IsProjectManager]

    def list(self, request, *args, **kwargs):
        today = timezone.now().date()
        start_of_week = today - timezone.timedelta(days=today.weekday())

        all_contractors = self.get_queryset()
        all_contractors_count = all_contractors.count()
        all_active_contractors_count = all_contractors.filter(is_still_active=True).count()

        total_contractors_monthly_pay = all_contractors.filter(paid__date__month=today.month).aggregate(total=Sum("paid__amount"))["total"] or 0.0

        total_contractors_weekly_pay = all_contractors.filter(paid__date__range=(start_of_week, today)).aggregate(total=Sum("paid__amount"))["total"] or 0.0

        page = self.paginate_queryset(all_contractors)
        if page is not None:
            data = self.serializer_class(page, many=True).data
            response_data = {
                "all_contractors_count": all_contractors_count,
                "all_active_contractors_count": all_active_contractors_count,
                "total_contractors_monthly_pay": total_contractors_monthly_pay,
                "total_contractors_weekly_pay": total_contractors_weekly_pay,
                "contractor": data,
            }
            return self.get_paginated_response(response_data)

        data = self.serializer_class(all_contractors, many=True).data
        response_data = {
            "all_contractors_count": all_contractors_count,
            "all_active_contractors_count": all_active_contractors_count,
            "total_contractors_monthly_pay": total_contractors_monthly_pay,
            "total_contractors_weekly_pay": total_contractors_weekly_pay,
            "contractor": data,
        }

        return Response(response_data)


class ApiSalaryWorkers(ModelViewSet):
    serializer_class = SalaryWorkersSerializer
    queryset = SalaryWorkers.objects.all()
    # permission_classes = [IsCEO | IsArtisanReadOnly]

    def list(self, request, *args, **kwargs):
        today = timezone.now().date()
        start_of_week = today - timezone.timedelta(days=today.weekday())

        all_salary_workers = self.get_queryset()
        salary_workers_count = all_salary_workers.count()
        active_salary_workers_count = all_salary_workers.filter(is_still_active=True).count()
        total_salary_workers_monthly_pay = all_salary_workers.aggregate(total=Sum("salary"))["total"] or 0.0
        total_paid = all_salary_workers.filter(paid__date__month=today.month).aggregate(total=Sum("paid__amount"))["total"] or 0.0

        page = self.paginate_queryset(all_salary_workers)
        if page is not None:
            data = self.serializer_class(page, many=True).data
            response_data = {
                "salary_workers_count": salary_workers_count,
                "active_salary_workers_count": active_salary_workers_count,
                "total_salary_workers_monthly_pay": total_salary_workers_monthly_pay,
                "total_paid": total_paid,
                "workers": data,
            }
            return self.get_paginated_response(response_data)

        data = self.serializer_class(all_salary_workers, many=True).data
        response_data = {
            "salary_workers_count": salary_workers_count,
            "active_salary_workers_count": active_salary_workers_count,
            "total_salary_workers_monthly_pay": total_salary_workers_monthly_pay,
            "total_paid": total_paid,
            "workers": data,
        }

        return Response(response_data)


class ApiSalaryWorkersRecord(ModelViewSet):
    serializer_class = SalaryWorkersRecordSerializer

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


class ApiAssets(ModelViewSet):
    serializer_class = AssetsSerializer
    queryset = Assets.objects.all().order_by('-is_still_available', '-date_added')
    pagination_class = AssetsPagination

    def list(self, request, *args, **kwargs):
        all_assets = self.get_queryset()
        all_assets_total = all_assets.filter(is_still_available=True).aggregate(Sum('value'))['value__sum'] or 0.0
        no_of_good_assets = all_assets.filter(is_still_available=True).count()
        no_of_bad_assets = all_assets.filter(is_still_available=False).count()
        total_assets_count = all_assets.count()

        page = self.paginate_queryset(all_assets)
        if page is not None:
            data = self.serializer_class(page, many=True).data
            response_data = {
                "total_assets_count": total_assets_count,
                "good_assets_count": no_of_good_assets,
                "good_assets_value": all_assets_total,
                "depreciated_assets_count": no_of_bad_assets,
                "assets": data
            }
            return self.get_paginated_response(response_data)

        data = self.serializer_class(all_assets, many=True).data
        response_data = {
            "total_assets_count": total_assets_count,
            "good_assets_count": no_of_good_assets,
            "good_assets_value": all_assets_total,
            "depreciated_assets_count": no_of_bad_assets,
            "assets": data
        }

        return Response(response_data)


class ApiOtherProductionRecord(ModelViewSet):
    serializer_class = OtherProductionSerializer

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


class ApiPaid(ModelViewSet):
    serializer_class = PaidSerializer
    queryset = Paid.objects.all().order_by('-date')
    filter_class = PaidFilter

    def list(self, request, *args, **kwargs):
        filterset = self.filter_class(request.GET, queryset=self.get_queryset())
        filtered_paid = filterset.qs.order_by('-date')

        # Group paid records by day
        daily_data = []
        current_date = None
        daily_payments = []

        for payment in filtered_paid:
            payment_date = payment.date

            if payment_date != current_date:
                if daily_payments:
                    daily_data.append({
                        "date": current_date,
                        "entries": PaidSerializer(daily_payments, many=True).data,
                        "daily_total": sum(p.amount for p in daily_payments),
                    })
                current_date = payment_date
                daily_payments = [payment]
            else:
                daily_payments.append(payment)

        if daily_payments:
            daily_data.append({
                "date": current_date,
                "entries": PaidSerializer(daily_payments, many=True).data,
                "daily_total": sum(p.amount for p in daily_payments),
            })

        # Weekly, monthly, and yearly totals
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())

        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)

        if year and not month:
            monthly_data = []
            for m in range(1, 13):
                monthly_expenses = filtered_paid.filter(date__year=year, date__month=m)
                total_for_the_month = monthly_expenses.aggregate(Sum('amount'))['amount__sum'] or 0.0

                if monthly_expenses.exists():
                    entries = []
                    for expense in monthly_expenses:
                        entries.append(PaidSerializer(expense).data)

                    monthly_data.append({
                        "month": f"{year}-{m:02d}",
                        "entries": entries,
                        "total_for_the_month": total_for_the_month,
                    })

            yearly_total = filtered_paid.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0

            response_data = {
                "monthly_total": filtered_paid.filter(date__month=today.month).aggregate(Sum('amount'))[
                                     'amount__sum'] or 0.0,
                "weekly_total": filtered_paid.filter(date__range=[start_of_week, today]).aggregate(Sum('amount'))[
                                    'amount__sum'] or 0.0,
                "daily_data": daily_data,
                "monthly_data": monthly_data,
                "yearly_total": yearly_total,
            }
        else:
            if year and month:
                monthly_total = filtered_paid.filter(date__year=year, date__month=month).aggregate(Sum('amount'))[
                                    'amount__sum'] or 0.0
            else:
                monthly_total = filtered_paid.filter(date__month=today.month).aggregate(Sum('amount'))[
                                    'amount__sum'] or 0.0

            response_data = {
                "monthly_total": monthly_total,
                "weekly_total": filtered_paid.filter(date__range=[start_of_week, today]).aggregate(Sum('amount'))[
                                    'amount__sum'] or 0.0,
                "daily_data": daily_data,
            }

            if year:
                yearly_total = filtered_paid.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0
                response_data["yearly_total"] = yearly_total

        return Response(response_data)
