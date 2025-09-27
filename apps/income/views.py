from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from .models import Income, IncomeCategory, Balance, BalanceSwitchLog
from .serializers import (
    IncomeCategorySerializer, IncomeSerializer, IncomeSerializerView,
    BalanceSwitchLogSerializer
)
from .filters import IncomeFilter
from api.permissions import CheckUserRoles
from django.db.models import F, Sum
from api.utils import swagger_helper
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from rest_framework.response import Response


class IncomeCategoryApi(ModelViewSet):
    queryset = IncomeCategory.objects.all()
    permission_classes = [CheckUserRoles]
    filter_backends = [SearchFilter]
    search_fields = ['name']
    required_roles = ['factory_manager', 'admin', 'ceo', 'accountant']
    serializer_class = IncomeCategorySerializer

    @swagger_helper("Income Categories", "Income Category")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Income Categories", "Income Category")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Income Categories", "Income Category")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Income Categories", "Income Category")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Income Categories", "Income Category")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Income Categories", "Income Category")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class IncomeApi(ModelViewSet):
    queryset = Income.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return IncomeSerializerView
        return IncomeSerializer

    filter_class = IncomeFilter
    permission_classes = [CheckUserRoles]
    required_roles = ['factory_manager', 'admin', 'ceo', 'accountant']


    @swagger_helper("Income", "Income")
    def list(self, request, *args, **kwargs):
        filterset = self.filter_class(request.GET, queryset=self.get_queryset())
        filtered_income = filterset.qs.order_by('-date', '-id')

        year = request.query_params.get('year', None)
        month = request.query_params.get('month', None)

        filtered = filtered_income
        balance, created = Balance.objects.get_or_create()
        # Always calculate totals for the current month
        today = timezone.now().date()
        current_month_total = filtered_income.filter(date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        current_month_cash_total = filtered_income.filter(cash=True, date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        current_month_bank_total = filtered_income.filter(cash=False, date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0.0
        cash_at_hand = balance.cash
        money_in_bank = balance.bank
        debt = balance.debt

        if year and not month:
            daily_data = []
            for m in range(1, 13):
                monthly_income = filtered_income.filter(date__year=year, date__month=m)
                total_for_the_month = monthly_income.aggregate(Sum('amount'))['amount__sum'] or 0.0

                # Only include months with data
                if monthly_income.exists():
                    entries = []
                    for income in monthly_income:
                        entries.append(IncomeSerializerView(income, context={'request': request}).data)

                    daily_data.append({
                        "month": f"{year}-{m:02d}",
                        "entries": entries,
                        "total_for_the_month": total_for_the_month,
                    })

            yearly_total = filtered_income.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0

            response_data = {
                "monthly_total": float(current_month_total),
                "current_month_cash_total": float(current_month_cash_total),
                "current_month_bank_total": float(current_month_bank_total),
                "cash_at_hand": float(cash_at_hand),
                "money_in_bank": float(money_in_bank),
                "debt": float(debt),
                "daily_data": daily_data,
                "yearly_total": float(yearly_total),
            }
            return Response(response_data)

        if year is None and month is None:
            filtered = filtered_income.filter(date__year=today.year, date__month=today.month)
        if year is None and month is not None:
            filtered = filtered_income.filter(date__year=today.year, date__month=month)

        daily_data = []
        current_date = None
        daily_income = []

        for income in filtered:
            income_date = income.date

            if income_date != current_date:
                if daily_income:
                    daily_data.append({
                        "date": current_date,
                        "entries": IncomeSerializerView(daily_income, many=True, context={'request': request}).data,
                        "daily_total": sum(e.amount for e in daily_income),
                    })
                current_date = income_date
                daily_income = [income]
            else:
                daily_income.append(income)

        if daily_income:
            daily_data.append({
                "date": current_date,
                "entries": IncomeSerializerView(daily_income, many=True, context={'request': request}).data,
                "daily_total": sum(e.amount for e in daily_income),
            })

        response_data = {
            "monthly_total": float(current_month_total),
            "current_month_cash_total": float(current_month_cash_total),
            "current_month_bank_total": float(current_month_bank_total),
            "cash_at_hand": float(cash_at_hand),
            "money_in_bank": float(money_in_bank),
            "debt": float(debt),
            "daily_data": daily_data,
        }

        if year:
            yearly_total = filtered_income.filter(date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0.0
            response_data["yearly_total"] = float(yearly_total)

        return Response(response_data)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        cash = validated_data.get('cash', False)
        amount = validated_data.get('amount', Decimal("0"))

        balance, created = Balance.objects.get_or_create(id=1)

        if cash:
            balance.cash += amount
        else:
            balance.bank += amount

        balance.save()
        serializer.save()

    def perform_update(self, serializer):
        with transaction.atomic():
            income = self.get_object()
            validated_data = serializer.validated_data
            new_cash = validated_data['cash']
            new_amount = validated_data['amount']
            balance, created = Balance.objects.get_or_create(id=1)
            amount_diff = new_amount - income.amount
            if income.cash != new_cash:
                if income.cash and not new_cash:
                    balance.cash -= income.amount
                    balance.bank += new_amount
                elif not income.cash and new_cash:
                    balance.bank -= income.amount
                    balance.cash += new_amount
            else:
                if income.cash:
                    if amount_diff > 0:
                        balance.cash += amount_diff
                    elif amount_diff < 0:
                        balance.cash -= abs(amount_diff)
                else:
                    if amount_diff > 0:
                        balance.bank += amount_diff
                    elif amount_diff < 0:
                        balance.bank -= abs(amount_diff)
            balance.save()
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            balance, created = Balance.objects.get_or_create(id=1)
            if instance.cash:
                balance.cash -= instance.amount
            else:
                balance.bank -= instance.amount
            balance.save()
            instance.delete()

    @swagger_helper("Income", "Income")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_helper("Income", "Income")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Income", "Income")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_helper("Income", "Income")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Income", "Income")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class BalanceSwitchApi(ModelViewSet):
    queryset = BalanceSwitchLog.objects.all().order_by("-switch_date")
    serializer_class = BalanceSwitchLogSerializer
    permission_classes = [CheckUserRoles]
    pagination_class = PageNumberPagination
    required_roles = ['factory_manager', 'admin', 'ceo', 'accountant']

    @swagger_helper("Balance Switch Log", "Balance Switch Log")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_helper("Balance Switch Log", "Balance Switch Log")
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from_method = serializer.validated_data['from_method']
        to_method = serializer.validated_data['to_method']
        amount = serializer.validated_data['amount']
        switch_date = serializer.validated_data.get('switch_date', date.today())

        with transaction.atomic():
            balance, _ = Balance.objects.get_or_create(id=1)
            if from_method == 'CASH':
                balance.cash -= amount
            elif from_method == 'BANK':
                balance.bank -= amount
            elif from_method == 'DEBT':
                balance.debt -= amount
            if to_method == 'CASH':
                balance.cash += amount
            elif to_method == 'BANK':
                balance.bank += amount
            elif to_method == 'DEBT':
                balance.debt += amount
            balance.save()
            balance_switch = BalanceSwitchLog.objects.create(
                balance=balance,
                from_method=from_method,
                to_method=to_method,
                amount=amount,
                switch_date=switch_date
            )
            return Response(self.get_serializer(balance_switch).data, status=201)


    @swagger_helper("Balance Switch Log", "Balance Switch Log")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_helper("Balance Switch Log", "Balance Switch Log")
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        from_method = serializer.validated_data.get('from_method', instance.from_method)
        to_method = serializer.validated_data.get('to_method', instance.to_method)
        amount = serializer.validated_data.get('amount', instance.amount)
        switch_date = serializer.validated_data.get('switch_date', instance.switch_date)

        with transaction.atomic():
            balance, _ = Balance.objects.get_or_create(id=1)
            # Reverse the original transfer
            if instance.from_method == 'CASH':
                balance.cash += instance.amount
            elif instance.from_method == 'BANK':
                balance.bank += instance.amount
            elif instance.from_method == 'DEBT':
                balance.debt += instance.amount
            if instance.to_method == 'CASH':
                balance.cash -= instance.amount
            elif instance.to_method == 'BANK':
                balance.bank -= instance.amount
            elif instance.to_method == 'DEBT':
                balance.debt -= instance.amount
            # Apply the new transfer
            if from_method == 'CASH':
                balance.cash -= amount
            elif from_method == 'BANK':
                balance.bank -= amount
            elif from_method == 'DEBT':
                balance.debt -= amount
            if to_method == 'CASH':
                balance.cash += amount
            elif to_method == 'BANK':
                balance.bank += amount
            elif to_method == 'DEBT':
                balance.debt += amount
            balance.save()
            instance.from_method = from_method
            instance.to_method = to_method
            instance.amount = amount
            instance.switch_date = switch_date
            instance.save()
            return Response(self.get_serializer(instance).data)

    @swagger_helper("Balance Switch Log", "Balance Switch Log")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_helper("Balance Switch Log", "Balance Switch Log")
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        with transaction.atomic():
            balance, _ = Balance.objects.get_or_create(id=1)
            # Reverse the original transfer
            if instance.from_method == 'CASH':
                balance.cash += instance.amount
            elif instance.from_method == 'BANK':
                balance.bank += instance.amount
            elif instance.from_method == 'DEBT':
                balance.debt += instance.amount
            if instance.to_method == 'CASH':
                balance.cash -= instance.amount
            elif instance.to_method == 'BANK':
                balance.bank -= instance.amount
            elif instance.to_method == 'DEBT':
                balance.debt -= instance.amount
            balance.save()
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)