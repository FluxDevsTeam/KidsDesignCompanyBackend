from django.db import transaction
from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F
from django.db.models.functions import Round, Coalesce
from django.db.models import IntegerField

from .models import Expense, ExpenseCategory, Assets
from .serializers import (
    ExpenseSerializer, ExpenseCategorySerializer, AssetsSerializer
)
from .filters import ExpenseFilter
from api.permissions import CheckUserRoles
from api.utils import swagger_helper
from .pagination import AssetsPagination
from django.utils import timezone
from rest_framework.response import Response


class ApiExpenseCategory(ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    filter_backends = [SearchFilter]
    search_fields = ['name']
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo', 'accountant']

    @swagger_helper("Expense Categories", "Expense Category")
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_helper("Expense Categories", "Expense Category")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Expense Categories", "Expense Category")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Expense Categories", "Expense Category")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Expense Categories", "Expense Category")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Expense Categories", "Expense Category")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ApiExpense(ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()
    filter_class = ExpenseFilter
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo', 'accountant']

    @swagger_helper("Expense", "Expense")
    def perform_create(self, serializer):
        with transaction.atomic():
            validated_data = serializer.validated_data
            payment_method = validated_data['payment_method']
            amount = validated_data['amount']
            balance, created = Balance.objects.get_or_create(id=1)
            if payment_method == 'CASH':
                balance.cash -= amount
            elif payment_method == 'BANK':
                balance.bank -= amount
            elif payment_method == 'DEBT':
                balance.debt += amount
            balance.save()
            serializer.save()

    @swagger_helper("Expense", "Expense")
    def perform_update(self, serializer):
        with transaction.atomic():
            instance = self.get_object()
            validated_data = serializer.validated_data
            new_payment_method = validated_data['payment_method']
            new_amount = validated_data['amount']
            balance, created = Balance.objects.get_or_create(id=1)
            amount_diff = new_amount - instance.amount
            if instance.payment_method != new_payment_method:
                if instance.payment_method == 'CASH' and new_payment_method == 'BANK':
                    balance.cash += instance.amount
                    balance.bank -= new_amount
                elif instance.payment_method == 'CASH' and new_payment_method == 'DEBT':
                    balance.cash += instance.amount
                    balance.debt += new_amount
                elif instance.payment_method == 'BANK' and new_payment_method == 'CASH':
                    balance.bank += instance.amount
                    balance.cash -= new_amount
                elif instance.payment_method == 'BANK' and new_payment_method == 'DEBT':
                    balance.bank += instance.amount
                    balance.debt += new_amount
                elif instance.payment_method == 'DEBT' and new_payment_method == 'CASH':
                    balance.debt -= instance.amount
                    balance.cash -= new_amount
                elif instance.payment_method == 'DEBT' and new_payment_method == 'BANK':
                    balance.debt -= instance.amount
                    balance.bank -= new_amount
            else:
                if instance.payment_method == 'CASH':
                    if amount_diff > 0:
                        balance.cash -= amount_diff
                    elif amount_diff < 0:
                        balance.cash += abs(amount_diff)
                elif instance.payment_method == 'BANK':
                    if amount_diff > 0:
                        balance.bank -= amount_diff
                    elif amount_diff < 0:
                        balance.bank += abs(amount_diff)
                elif instance.payment_method == 'DEBT':
                    if amount_diff > 0:
                        balance.debt += amount_diff
                    elif amount_diff < 0:
                        balance.debt -= abs(amount_diff)
            balance.save()
            serializer.save()

    @swagger_helper("Expense", "Expense")
    def perform_destroy(self, instance):
        with transaction.atomic():
            balance, created = Balance.objects.get_or_create(id=1)
            if instance.payment_method == 'CASH':
                balance.cash += instance.amount
            elif instance.payment_method == 'BANK':
                balance.bank += instance.amount
            elif instance.payment_method == 'DEBT':
                balance.debt -= instance.amount
            balance.save()
            instance.delete()

    @swagger_helper("Expense", "Expense")
    def list(self, request, *args, **kwargs):
        filterset = self.filter_class(request.GET, queryset=self.get_queryset())
        filtered_expenses = filterset.qs.order_by('-date', '-id')
        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)
        filtered = filtered_expenses
        today = timezone.now().date()
        current_month_total = filtered_expenses.filter(date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        current_month_project_total = filtered_expenses.filter(project__isnull=False, date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        current_month_shop_total = filtered_expenses.filter(shop__isnull=False, date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        current_month_product_total = filtered_expenses.filter(product__isnull=False, date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        if year and not month:
            data = []
            for m in range(1, 13):
                monthly_expenses = filtered_expenses.filter(date__year=year, date__month=m)
                total_for_the_month = monthly_expenses.aggregate(Sum('amount'))['amount__sum'] or 0.0
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
                "current_month_product_total": float(current_month_product_total),
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
            "current_month_product_total": float(current_month_product_total),
            "daily_data": daily_data,
        }
        if year:
            yearly_total = filtered_expenses.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0
            response_data["yearly_total"] = float(yearly_total)
        return Response(response_data)

    @swagger_helper("Expense", "Expense")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Expense", "Expense")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Expense", "Expense")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Expense", "Expense")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Expense", "Expense")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class ApiAssets(ModelViewSet):
    serializer_class = AssetsSerializer
    queryset = Assets.objects.all().order_by('-is_still_available', '-date_added')
    pagination_class = AssetsPagination
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo', 'accountant']
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_still_available']
    search_fields = ['name']

    @swagger_helper("Asset", "Asset")
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

    @swagger_helper("Asset", "Asset")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Asset", "Asset")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Asset", "Asset")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Asset", "Asset")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Asset", "Asset")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
