from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models.functions import Coalesce
from django.db.models import Sum, F
from django.db.models import IntegerField, DecimalField
from rest_framework.response import Response

from .models import Customer
from .serializers import CustomerSerializer, CustomerDetailSerializer
from .filters import CustomerFilter
from api.permissions import CheckUserRoles
from api.utils import swagger_helper

class ApiCustomer(ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'project_manager', 'ceo', 'shopkeeper']
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CustomerFilter
    search_fields = ['name', 'address']

    @swagger_helper("Customer", "Customer")
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        customer = Customer.objects.all()
        all_customers_count = customer.count()
        active_customers = customer.filter(project__is_delivered=False).distinct().count()
        owing_customers = customer.filter(project__balance__gt=0).distinct().count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            response_data = {
                "all_customers_count": all_customers_count,
                "active_customers": active_customers,
                "owing_customers": owing_customers,
                "all_customers": data
            }
            return self.get_paginated_response(response_data)

        data = self.get_serializer(queryset, many=True).data
        response_data = {
            "all_customers_count": all_customers_count,
            "active_customers": active_customers,
            "owing_customers": owing_customers,
            "all_customers": data
        }
        return Response(response_data)


    @swagger_helper("Customer", "Customer")
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


    @swagger_helper("Customer", "Customer")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Customer", "Customer")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Customer", "Customer")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Customer", "Customer")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
