from customers.models import Customer
from expensis.models import Expense
from datetime import datetime
import django_filters

from project.models import Project
from shop.models import InventoryItem, AddStock, Sold
import datetime

from store.models import AddRawMaterials, RawMaterial, Removed
from workers.models import Paid


class AddStockFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = AddStock
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if not value:
            value = datetime.now().month
        return queryset.filter(date__month=int(value))

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=int(value))

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=int(value))


class AddRawMaterialsFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = AddRawMaterials
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if not value:
            value = datetime.now().month
        return queryset.filter(date__month=int(value))

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=int(value))

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=int(value))


class ExpenseFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = Expense
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if not value:
            value = datetime.now().month
        return queryset.filter(date__month=int(value))

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=int(value))

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=int(value))


class IncomeFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = Expense
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if not value:
            value = datetime.now().month
        return queryset.filter(date__month=int(value))

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=int(value))

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=int(value))


class SoldFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = Sold
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if not value:
            value = datetime.now().month
        return queryset.filter(date__month=int(value))

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=int(value))

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=int(value))


class RemovedFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = Removed
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if not value:
            value = datetime.now().month
        return queryset.filter(date__month=int(value))

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=int(value))

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=int(value))


class InventoryItemFilter(django_filters.FilterSet):
    archived = django_filters.BooleanFilter(field_name='archived')
    empty_stock = django_filters.BooleanFilter(method='filter_empty_stock', label='Empty Stock')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock', label='Low Stock (<10)')
    category = django_filters.NumberFilter(field_name='category', lookup_expr='exact')
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')

    class Meta:
        model = InventoryItem
        fields = ['archived', 'category', 'category_name']

    def filter_empty_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock=0, archived=False)
        return queryset

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__lt=10, archived=False)
        return queryset


class RawMaterialFilter(django_filters.FilterSet):
    archived = django_filters.BooleanFilter(field_name='archived')
    empty_stock = django_filters.BooleanFilter(method='filter_empty_stock', label='Empty Stock')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock', label='Low Stock (<10)')
    category = django_filters.NumberFilter(field_name='category', lookup_expr='exact')
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')

    class Meta:
        model = RawMaterial
        fields = ['archived', 'category', 'category_name']

    def filter_empty_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity=0, archived=False)
        return queryset

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity__lt=10, archived=False)
        return queryset


class ProjectFilter(django_filters.FilterSet):
    archived = django_filters.BooleanFilter(field_name='archived')
    deadline = django_filters.BooleanFilter(method='filter_deadline', label='Past Deadline')
    upcoming_deadline = django_filters.BooleanFilter(method='filter_upcoming_deadline', label='Deadline within 2 Weeks')
    is_delivered = django_filters.BooleanFilter(field_name='is_delivered')

    class Meta:
        model = Project
        fields = ['archived', 'is_delivered']

    def filter_deadline(self, queryset, name, value):
        if value:
            today = datetime.date.today()
            return queryset.filter(deadline__lt=today)
        return queryset

    def filter_upcoming_deadline(self, queryset, name, value):
        if value:
            today = datetime.date.today()
            two_weeks = today + datetime.timedelta(days=14)
            return queryset.filter(deadline__lte=two_weeks)
        return queryset


class CustomerFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(method='filter_active', field_name='active')
    owing = django_filters.BooleanFilter(method='filter_owing', field_name='owing')

    class Meta:
        model = Customer

    def filter_active(self, queryset, name, value):
        if value:
            return queryset.filter(project__is_delivered=False).distinct()
        return queryset

    def filter_owing(self, queryset, name, value):
        if value:
            return queryset.filter(project__balance__gt=0).distinct()
        return queryset


class PaidFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = Paid
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if not value:
            value = datetime.now().month
        return queryset.filter(date__month=int(value))

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=int(value))

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=int(value))