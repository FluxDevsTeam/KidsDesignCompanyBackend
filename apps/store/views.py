from django.db import transaction
from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, F
from django.db.models.functions import Round
from django.db.models import IntegerField

from .models import RawMaterial, Removed, StoreCategory, AddRawMaterials
from .serializers import (
    RawMaterialSerializer, RemovedSerializer, StoreCategorySerializer,
    AddRawMaterialsSerializer
)
from .filters import AddRawMaterialsFilter, RawMaterialFilter, RemovedFilter
from api.permissions import CheckUserRoles
from .utils import swagger_helper

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

    @swagger_helper("Raw Materials", "Raw Material")
    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            AddRawMaterials.objects.create(item=instance, quantity=instance.quantity, cost_price=instance.price, name=instance.name)


    @swagger_helper("Raw Materials", "Raw Material")
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


    @swagger_helper("Raw Materials", "Raw Material")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Raw Materials", "Raw Material")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Raw Materials", "Raw Material")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Raw Materials", "Raw Material")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Raw Materials", "Raw Material")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiRemoved(ModelViewSet):
    serializer_class = RemovedSerializer
    queryset = Removed.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = RemovedFilter
    search_fields = ['material__name', 'product__name', 'material__description']
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'ceo']

    @swagger_helper("Removed Items", "Removed Item")
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

    @swagger_helper("Removed Items", "Removed Item")
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

    @swagger_helper("Removed Items", "Removed Item")
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

    @swagger_helper("Removed Items", "Removed Item")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Removed Items", "Removed Item")
    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    @swagger_helper("Removed Items", "Removed Item")
    def partial_update(self, request, *args, **kwargs):
        material = request.data.get("material")
        quantity = request.data.get("quantity")
        product = request.data.get("product")
        date = request.data.get("date")
        removed_item = self.get_object()

        if not material and not quantity and not product and not date:
            return Response(
                {"error": "Either one or more of 'material', 'quantity', 'product' or 'date'' is required."}, status=status.HTTP_400_BAD_REQUEST)
        if date:
            try:
                removed_item.date = date
                removed_item.save()
            except:
                return Response(
                    {"error": "date format is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

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



class ApiStoreCategory(ModelViewSet):
    queryset = StoreCategory.objects.all()
    serializer_class = StoreCategorySerializer
    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper', 'ceo']
    filter_backends = [SearchFilter]
    search_fields = ['name']


    @swagger_helper("Store Categories", "Store Category")
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


    @swagger_helper("Store Categories", "Store Category")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Store Categories", "Store Category")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Store Categories", "Store Category")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Store Categories", "Store Category")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Store Categories", "Store Category")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiAddRawMaterials(ModelViewSet):
    serializer_class = AddRawMaterialsSerializer
    queryset = AddRawMaterials.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AddRawMaterialsFilter
    search_fields = ['item__name']

    permission_classes = [CheckUserRoles]
    required_roles = ['storekeeper','ceo']

    @swagger_helper("Add Raw Materials", "Add Raw Materials")
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

    @swagger_helper("Add Raw Materials", "Add Raw Materials")
    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    @swagger_helper("Add Raw Materials", "Add Raw Materials")
    def partial_update(self, request, *args, **kwargs):
        quantity = request.data.get("quantity")
        date = request.data.get("date")

        try:
            quantity = Decimal(quantity)
        except ValueError:
            return Response({"error": "Invalid quantity format"}, status=status.HTTP_400_BAD_REQUEST)

        if not quantity and not date:
            return Response({"error": "at least one of date and quantity is required"})

        if quantity <= 0:
            return Response({"error": "quantity  most be a positive number"})

        added_material = self.get_object()
        with transaction.atomic():
            if date:
                try:
                    added_material.date = date
                    added_material.save()
                except:
                    return Response(
                        {"error": "date format is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

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


    @swagger_helper("Add Raw Materials", "Add Raw Materials")
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

    @swagger_helper("Add Raw Materials", "Add Raw Materials")
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

    @swagger_helper("Add Raw Materials", "Add Raw Materials")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Add Raw Materials", "Add Raw Materials")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

