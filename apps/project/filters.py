import django_filters
from datetime import datetime
from .models import Project

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
