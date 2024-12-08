import uuid
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from django.db.models import F

from .permissions import IsCEO, IsArtisan, IsStoreKeeper, IsProjectManager, IsOwnerOrAdmin, IsAdminOrReadOnly
from django.conf import settings
from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from .seralizers import InventoryItemSerializer, SoldSerializer, CustomerSerializer, ExpenseSerializer, QuotationSerializer, ProductSerializer, RawMaterialSerializer, RawMaterialUsedSerializer, ProjectSerializer, RemovedSerializer, ContractorsSerializer, SalaryWorkersSerializer
from shop.models import InventoryItem, Sold
from customers.models import Customer
from expensis.models import Expense
from products.models import ListField, Quotation, RawMaterialUsed, Product
from project.models import Project
from store.models import RawMaterial, Removed
from workers.models import Contractors, SalaryWorkers


class ApiInventoryItem(ModelViewSet):
    serializer_class = InventoryItemSerializer
    queryset = InventoryItem.objects.all()

    permission_classes = [IsCEO]
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # filterset_fields = ['origin', 'destination']
    # ordering_fields = ['departure_date', 'price']


class ApiSold(ModelViewSet):
    serializer_class = SoldSerializer
    queryset = Sold.objects.all()
    permission_classes = [IsCEO]


class ApiCustomer(ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    permission_classes = [IsCEO]


class ApiExpense(ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()
    permission_classes = [IsCEO]


class ApiQuotation(ModelViewSet):
    serializer_class = QuotationSerializer
    queryset = Quotation.objects.all()
    permission_classes = [IsCEO]


class ApiRawMaterialUsed(ModelViewSet):
    serializer_class = RawMaterialUsedSerializer
    queryset = RawMaterialUsed.objects.all()


class ApiProduct(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()


class ApiProject(ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()


class ApiRawMaterial(ModelViewSet):
    serializer_class = RawMaterialSerializer
    queryset = RawMaterial.objects.all()


class ApiRemoved(ModelViewSet):
    serializer_class = RemovedSerializer
    queryset = Removed.objects.all()


class ApiContractors(ModelViewSet):
    serializer_class = ContractorsSerializer
    queryset = Contractors.objects.all()


class ApiSalaryWorkers(ModelViewSet):
    serializer_class = SalaryWorkersSerializer
    queryset = SalaryWorkers.objects.all()
