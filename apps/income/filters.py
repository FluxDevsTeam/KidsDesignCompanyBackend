import django_filters
from datetime import datetime
from .models import Income

class IncomeFilter(django_filters.FilterSet):
    month = django_filters.NumberFilter(field_name='date__month', method='filter_by_month', required=False)
    year = django_filters.NumberFilter(field_name='date__year', method='filter_by_year', required=False)
    day = django_filters.NumberFilter(field_name='date__day', method='filter_by_day', required=False)

    class Meta:
        model = Income
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
