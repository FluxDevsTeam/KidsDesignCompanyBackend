from django.db.models import Sum
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .models import Assets


class AssetsPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        # Compute total value for assets that are still available.
        total_value = Assets.objects.filter(is_still_available=True).aggregate(total=Sum('value'))['total'] or 0
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_value': total_value,  # total appears once at the top level
            'results': data
        })