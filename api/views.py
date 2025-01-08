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
    permission_classes = [IsCEO | IsStoreKeeper | IsManager]


class ApiSold(ModelViewSet):
    serializer_class = SoldSerializer
    queryset = Sold.objects.all()
    permission_classes = [IsCEO | IsStoreKeeper]

    @action(methods=["POST"], detail=False)
    def sell(self, request):
        item = request.data.get("item")
        quantity = request.data.get("quantity")
        items = InventoryItem.objects.get(id=item.id)
        print(items.id)
        print(items)
        print("here")
        print("here")
        print("here")
        if not item and not quantity:
            return Response({"error": "both item and quantity are required"}, status=status.HTTP_400_BAD_REQUEST)
        Sold.objects.create(item=item, quantity=quantity)


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
    permission_classes = [IsCEO | IsProjectManager]


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
    permission_classes = [IsCEO | IsStoreKeeper]


class ApiContractors(ModelViewSet):
    serializer_class = ContractorsSerializer
    queryset = Contractors.objects.all()
    permission_classes = [IsCEO | IsArtisanReadOnly | IsProjectManager]


class ApiSalaryWorkers(ModelViewSet):
    serializer_class = SalaryWorkersSerializer
    queryset = SalaryWorkers.objects.all()
    permission_classes = [IsCEO | IsArtisanReadOnly]
