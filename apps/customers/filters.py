import django_filters
from .models import Customer

class CustomerFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(method='filter_active', field_name='active')
    owing = django_filters.BooleanFilter(method='filter_owing', field_name='owing')

    class Meta:
        model = Customer
        fields = ['project__balance', 'project__is_delivered']

    def filter_active(self, queryset, name, value):
        if value:
            return queryset.filter(project__is_delivered=False).distinct()
        return queryset

    def filter_owing(self, queryset, name, value):
        if value:
            return queryset.filter(project__balance__gt=0).distinct()
        return queryset