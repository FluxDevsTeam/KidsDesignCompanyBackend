import django_filters
from expensis.models import Expense
from datetime import datetime


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
        return queryset.filter(date__month=value)

    def filter_by_year(self, queryset, name, value):
        if not value:
            value = datetime.now().year
        return queryset.filter(date__year=value)

    def filter_by_day(self, queryset, name, value):
        if not value:
            value = datetime.now().day
        return queryset.filter(date__day=value)
