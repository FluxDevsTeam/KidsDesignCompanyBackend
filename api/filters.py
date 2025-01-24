import django_filters
from expensis.models import Expense
from datetime import datetime


class ExpenseFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month')
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year')
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day')

    class Meta:
        model = Expense
        fields = ['month', 'year', 'day']

    def filter_by_month(self, queryset, name, value):
        if value:
            return queryset.filter(date__month=value)
        return queryset

    def filter_by_year(self, queryset, name, value):
        if value:
            return queryset.filter(date__year=value)
        return queryset

    def filter_by_day(self, queryset, name, value):
        if value:
            return queryset.filter(date__day=value)
        return queryset
