from rest_framework import permissions


class IsStoreKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__iexact='storekeeper').exists()

class IsShopKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__iexact='shopkeeper').exists()

class IsFactoryManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__iexact='factory_manager').exists()

class IsProductManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__iexact='product_manager').exists()

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__iexact='admin').exists()

class IsCeo(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__iexact='ceo').exists() or request.user.is_superuser
