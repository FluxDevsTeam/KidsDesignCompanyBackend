from django.db import transaction
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action
from .permissions import IsCEO, IsArtisan, IsStoreKeeper, IsProjectManager, IsOwnerOrAdmin, IsAdminOrReadOnly, \
    IsArtisanReadOnly, IsStoreKeeperReadonly, IsManager
from rest_framework.viewsets import ModelViewSet
from .seralizers import InventoryItemSerializer, SoldSerializer, CustomerSerializer, ExpenseSerializer, \
    QuotationSerializer, ProductSerializer, RawMaterialSerializer, RawMaterialUsedSerializer, ProjectSerializer, \
    RemovedSerializer, ContractorsSerializer, SalaryWorkersSerializer
from shop.models import InventoryItem, Sold
from customers.models import Customer
from expensis.models import Expense
from products.models import Quotation, RawMaterialUsed, Product
from project.models import Project
from store.models import RawMaterial, Removed
from workers.models import Contractors, SalaryWorkers
from rest_framework import viewsets, status, permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class ApiInventoryItem(ModelViewSet):
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.all()
    # permission_classes = [IsCEO | IsStoreKeeper | IsManager]


class ApiSold(ModelViewSet):
    serializer_class = SoldSerializer
    queryset = Sold.objects.all()
    # permission_classes = [IsCEO | IsStoreKeeper]

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE")

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PATCH")

    @action(methods=["POST"], detail=False)
    def sell(self, request):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")

        if not item_id or not quantity:
            return Response(
                {"error": "Both 'item' and 'quantity' are required."}, status=status.HTTP_400_BAD_REQUEST)

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

        Sold.objects.create(item=inventory_item, quantity=quantity)
        inventory_item.stock -= quantity
        inventory_item.save()

        return Response(
            {"message": "Sale completed successfully."}, status=status.HTTP_200_OK)

    @action(methods=["PUT", "PATCH"], detail=True)
    def edit(self, request, pk):
        item_id = request.data.get("item")
        quantity = request.data.get("quantity")
        sold_item = get_object_or_404(Sold, id=pk)

        if not item_id and not quantity:
            return Response(
                {"error": "Either 'item' or 'quantity' or both is required."}, status=status.HTTP_400_BAD_REQUEST)

        if quantity is not None:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    return Response({"error": "Quantity must be a positive number."}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "quantity most be an number"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if item_id and int(item_id) != int(sold_item.item.id):

                old_inventory_item = get_object_or_404(InventoryItem, id=sold_item.item.id)
                old_inventory_item.stock += sold_item.quantity

                new_inventory_item = get_object_or_404(InventoryItem, id=item_id)

                if quantity is None:
                    quantity = sold_item.quantity
                if quantity > new_inventory_item.stock:
                    return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)

                old_inventory_item.save()
                new_inventory_item.stock -= quantity
                new_inventory_item.save()

                sold_item.item.id = item_id
                sold_item.quantity = quantity
                sold_item.save()

                return Response({"message": "Sale edited successfully."}, status=status.HTTP_200_OK)

            if quantity is not None and quantity != sold_item.quantity:
                inventory_item = get_object_or_404(InventoryItem, id=sold_item.item.id)
                difference = abs(quantity - sold_item.quantity)

                if quantity > sold_item.quantity:
                    if difference > inventory_item.stock:
                        return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)
                    inventory_item.stock -= difference
                else:
                    inventory_item.stock += difference

                inventory_item.save()
                sold_item.quantity = quantity
                sold_item.save()

                return Response({"message": "Sale quantity edited successfully."}, status=status.HTTP_200_OK)

            return Response({"message": "No changes made."}, status=status.HTTP_200_OK)

    @action(methods=["DELETE"], detail=True)
    def delete(self, request, pk):
        sold_item = get_object_or_404(Sold, id=pk)
        inventory_item = get_object_or_404(InventoryItem, pk=sold_item.item.id)
        inventory_item.stock += sold_item.quantity
        inventory_item.save()
        sold_item.delete()

        return Response({"message": "Sold item deleted and inventory updated."}, status=204)


class ApiCustomer(ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    permission_classes = [IsCEO | IsProjectManager]


class ApiExpense(ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()
    permission_classes = [IsCEO]


class ApiQuotation(ModelViewSet):
    serializer_class = QuotationSerializer
    queryset = Quotation.objects.all()
    permission_classes = [IsCEO | IsProjectManager | IsStoreKeeperReadonly]


class ApiRawMaterialUsed(ModelViewSet):
    serializer_class = RawMaterialUsedSerializer
    queryset = RawMaterialUsed.objects.all()
    permission_classes = [IsCEO | IsProjectManager | IsStoreKeeperReadonly]


class ApiProduct(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    # permission_classes = [IsCEO | IsProjectManager]


class ApiProject(ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    permission_classes = [IsCEO | IsProjectManager]


class ApiRawMaterial(ModelViewSet):
    serializer_class = RawMaterialSerializer
    queryset = RawMaterial.objects.all()
    permission_classes = [IsCEO | IsStoreKeeper]


class ApiRemoved(ModelViewSet):
    serializer_class = RemovedSerializer
    queryset = Removed.objects.all()
    # permission_classes = [IsCEO | IsStoreKeeper]


class ApiContractors(ModelViewSet):
    serializer_class = ContractorsSerializer
    queryset = Contractors.objects.all()
    permission_classes = [IsCEO | IsArtisanReadOnly | IsProjectManager]


class ApiSalaryWorkers(ModelViewSet):
    serializer_class = SalaryWorkersSerializer
    queryset = SalaryWorkers.objects.all()
    permission_classes = [IsCEO | IsArtisanReadOnly]
