import django_filters
from datetime import datetime
from .models import AddRawMaterials, RawMaterial, Removed

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

