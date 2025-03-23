from rest_framework import permissions


class IsCeo(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__iexact='ceo').exists() or request.user.is_superuser
