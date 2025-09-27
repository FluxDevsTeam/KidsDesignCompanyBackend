from django.db import transaction
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, F
from django.db.models.functions import Round
from django.db.models import IntegerField

from .models import Quotation, Product, ProductSalaryWorker, ProductContractor
from .serializers import (
    QuotationSerializer, ProductSerializer, RawMaterialUsedSerializer,
    ProductContractorSerializer, ProductSalaryWorkerSerializer
)
from api.permissions import CheckUserRoles
from django.contrib.auth import get_user_model
from .utils import swagger_helper

User = get_user_model()


class ApiQuotation(ModelViewSet):
    serializer_class = QuotationSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'factory_manager', 'project_manager', 'ceo']

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return Quotation.objects.filter(product=product_id)
    @swagger_helper("Quotation", "Quotation")
    def create(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @swagger_helper("Quotation", "Quotation")
    def update(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data)

    @swagger_helper("Quotation", "Quotation")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Quotation", "Quotation")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Quotation", "Quotation")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Quotation", "Quotation")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


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
    
    @swagger_helper("Raw Material Used", "Raw Material Used")
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        # Rename material__name to material_name in the response
        data = [{"material": item["material"], "material_name": item["material__name"], "total_quantity": item["total_quantity"]} for item in serializer.data]
        return Response(data)

    @swagger_helper("Raw Material Used", "Raw Material Used")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class ApiProductContractor(ModelViewSet):
    serializer_class = ProductContractorSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'factory_manager', 'project_manager', 'admin', 'ceo', 'accountant']

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return ProductContractor.objects.filter(product=product_id)

    @swagger_helper("Product Contractor", "Product Contractor")
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

    @swagger_helper("Product Contractor", "Product Contractor")
    def update(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data)

    @swagger_helper("Product Contractor", "Product Contractor")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Product Contractor", "Product Contractor")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Product Contractor", "Product Contractor")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Product Contractor", "Product Contractor")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiProductSalaryWorker(ModelViewSet):
    serializer_class = ProductSalaryWorkerSerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'project_manager', 'factory_manager', 'ceo']

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk')
        return ProductSalaryWorker.objects.filter(product=product_id)

    @swagger_helper("Product Salary Worker", "Product Salary Worker")
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

    @swagger_helper("Product Salary Worker", "Product Salary Worker")
    def update(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data)

    @swagger_helper("Product Salary Worker", "Product Salary Worker")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Product Salary Worker", "Product Salary Worker")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Product Salary Worker", "Product Salary Worker")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Product Salary Worker", "Product Salary Worker")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiProduct(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.prefetch_related("productcontractor_set", "productsalaryworker_set")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['project__name', 'name']
    ordering = ['progress']
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'shopkeeper', 'factory_manager', 'project_manager','ceo']

    @swagger_helper("Product", "Product")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Product", "Product")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Product", "Product")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Product", "Product")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Product", "Product")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Product", "Product")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
