from django.db import transaction
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from .permissions import IsCEO, IsArtisan, IsStoreKeeper, IsProjectManager, IsOwnerOrAdmin, IsAdminOrReadOnly, \
    IsArtisanReadOnly, IsStoreKeeperReadonly, IsManager
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .seralizers import InventoryItemSerializer, SoldSerializer, CustomerSerializer, ExpenseSerializer, \
    QuotationSerializer, ProductSerializer, RawMaterialSerializer, ProjectSerializer, RawMaterialUsedSerializer, \
    RemovedSerializer, ContractorsSerializer, SalaryWorkersSerializer, ExpenseCategorySerializer, AddSockSerializer, \
    InventoryCategorySerializer, ProductSalaryWorkerSerializer, ProductContractorSerializer, StoreCategorySerializer, \
    SalaryWorkersRecordSerializer, ContractorRecordSerializer, OverheadCostSerializer
from shop.models import InventoryItem, Sold, InventoryCategory, AddStock
from customers.models import Customer
from expensis.models import Expense, ExpenseCategory
from products.models import Quotation, Product, ProductSalaryWorker, ProductContractor
from project.models import Project, OverheadCost
from store.models import RawMaterial, Removed, StoreCategory
from workers.models import Contractors, SalaryWorkers, ContractorRecord, SalaryWorkersRecord
from rest_framework import viewsets, status, permissions, mixins
from django.contrib.auth import get_user_model
from .filters import ExpenseFilter, InventoryItemFilter, AddStockFilter, SoldFilter, ProjectFilter
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime
from django.db.models import F, ExpressionWrapper, DecimalField, Sum

User = get_user_model()


class ApiInventoryItem(ModelViewSet):
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.all()
    # permission_classes = [IsCEO | IsStoreKeeper | IsManager]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = InventoryItemFilter
    search_fields = ['name', 'description']

    def get_queryset(self):
        qs = super().get_queryset()
        if 'archived' not in self.request.query_params:
            qs = qs.filter(archived=False)
        return qs


class ApiAddStock(ModelViewSet):
    serializer_class = AddSockSerializer
    queryset = AddStock.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AddStockFilter
    search_fields = ['item__name']
    # permission_classes = [IsCEO | IsStoreKeeper | IsManager]

    def create(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")

        if not item_id:
            return Response({"error": "please input an item"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero")
        except (ValueError, TypeError):
            return Response({"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            item = get_object_or_404(InventoryItem, id=item_id)
            item.stock += quantity
            item.save()

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"success": "Item added successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        filtered_solds = filterset.qs.order_by('-date')
        daily_data = []
        current_date = None
        daily_solds = []
        for sold in filtered_solds:
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
        monthly_total = filtered_solds.aggregate(total=Sum(total_price_expr))['total'] or 0.0
        response_data = {
            "daily_data": daily_data,
            "monthly_total": monthly_total,
        }
        year = request.query_params.get('year', None)
        if year:
            yearly_total = self.get_queryset().filter(date__year=year).aggregate(total=Sum(total_price_expr))['total'] or 0.0
            response_data["yearly_total"] = yearly_total
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

        if (customer and (not logistics)) or (logistics and (not customer)):
            return Response(
                {"error": "both 'customer' and 'logistics' is required."}, status=status.HTTP_400_BAD_REQUEST)

        if project and logistics:
            return Response(
                {"error": "you cant set logistics for item sold in a project"}, status=status.HTTP_400_BAD_REQUEST)

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
            Sold.objects.create(item=inventory_item, quantity=quantity, customer=customer, cost_price=inventory_item.cost_price, selling_price=inventory_item.selling_price, project=project_instance)
        else:
            customer_data = get_object_or_404(Customer, id=customer)
            Sold.objects.create(item=inventory_item, quantity=quantity, customer=customer_data, cost_price=inventory_item.cost_price, selling_price=inventory_item.selling_price, logistics=logistics)

        inventory_item.stock -= quantity
        inventory_item.save()
        return Response(
            {"message": "Sale completed successfully."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        sold_item = self.get_object()
        inventory_item = get_object_or_404(InventoryItem, pk=sold_item.item.id)
        inventory_item.stock += sold_item.quantity
        inventory_item.save()
        sold_item.delete()

        return Response({"message": "Sold item deleted and inventory updated."}, status=204)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")
        selling_price = request.data.get("selling_price")
        cost_price = request.data.get("cost_price")
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

        if all(field is None for field in [item_id, quantity, selling_price, cost_price, project, customer, logistics]):
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

        if cost_price is not None:
            try:
                cost_price = float(cost_price)
                if cost_price <= 0:
                    return Response({"error": "cost_price must be a positive number."}, status=status.HTTP_400_BAD_REQUEST)

            except ValueError:
                return Response({"error": "cost_price most be a number"}, status=status.HTTP_400_BAD_REQUEST)

        if selling_price is not None:
            try:
                selling_price = float(selling_price)
                if selling_price <= 0:
                    return Response({"error": "selling_price must be a positive number."},
                                    status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "selling_price most be a number"}, status=status.HTTP_400_BAD_REQUEST)

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

                if cost_price and float(cost_price) != float(sold_item.cost_price):
                    sold_item.cost_price = cost_price
                    updated_fields.append("cost price")

                if selling_price and float(selling_price) != float(sold_item.selling_price):
                    sold_item.selling_price = selling_price
                    updated_fields.append("selling price")

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

                if cost_price and float(cost_price) != float(sold_item.cost_price):
                    sold_item.cost_price = cost_price
                    updated_fields.append("cost price")

                if selling_price and float(selling_price) != float(sold_item.selling_price):
                    sold_item.selling_price = selling_price
                    updated_fields.append("selling price")

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

            if cost_price and float(cost_price) != float(sold_item.cost_price):
                sold_item.cost_price = cost_price
                updated_fields.append("cost price")

            if selling_price and float(selling_price) != float(sold_item.selling_price):
                sold_item.selling_price = selling_price
                updated_fields.append("selling price")

            if logistics and logistics != sold_item.logistics:
                sold_item.logistics = logistics
                updated_fields.append("logistics")

            # Save only if something was updated
            if updated_fields:
                sold_item.save()
                return Response({"data": f"{', '.join(updated_fields)} updated successfully"}, status=status.HTTP_200_OK)

            return Response({"message": "No changes made."}, status=status.HTTP_200_OK)


class ApiCustomer(ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    # permission_classes = [IsCEO | IsProjectManager]


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

        daily_data = []
        current_date = None
        daily_expenses = []
        for expense in filtered_expenses:

            if expense.date.date() != current_date:
                if daily_expenses:
                    daily_data.append({
                        "date": current_date,
                        "entries": ExpenseSerializer(daily_expenses, many=True).data,
                        "daily_total": sum(e.amount for e in daily_expenses),
                    })
                current_date = expense.date.date()
                daily_expenses = [expense]
            else:
                daily_expenses.append(expense)

        if daily_expenses:
            daily_data.append({
                "date": current_date,
                "entries": ExpenseSerializer(daily_expenses, many=True).data,
                "daily_total": sum(e.amount for e in daily_expenses),
            })

        monthly_total = filtered_expenses.aggregate(Sum('amount'))['amount__sum'] or 0.0

        response_data = {
            "daily_data": daily_data,
            "monthly_total": monthly_total,
        }

        year = request.query_params.get('year', None)
        if year:
            yearly_total = Expense.objects.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0
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


class ApiProject(ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    # permission_classes = [IsCEO | IsProjectManager]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProjectFilter
    search_fields = ['customer__name', 'name']

    def get_queryset(self):
        qs = super().get_queryset()
        if 'archived' not in self.request.query_params:
            qs = qs.filter(archived=False)
        return qs

class ApiRawMaterial(ModelViewSet):
    serializer_class = RawMaterialSerializer
    queryset = RawMaterial.objects.all()
    # permission_classes = [IsCEO | IsStoreKeeper]


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

        Removed.objects.create(material=material_data, quantity=quantity, product=product_data)
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


class ApiSalaryWorkers(ModelViewSet):
    serializer_class = SalaryWorkersSerializer
    queryset = SalaryWorkers.objects.all()
    # permission_classes = [IsCEO | IsArtisanReadOnly]


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