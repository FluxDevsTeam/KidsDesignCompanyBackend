from rest_framework import permissions


class IsAdminOrReadOnly(permissions.IsAdminUser):
    def has_permission(self, request, view):
        admin_permission = super().has_permission(request, view)
        return request.method == 'GET' or admin_permission


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        if request.user.is_staff:
            return True

        return obj.owner == request.user


from rest_framework import permissions


class IsCEO(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='CEO').exists()


class IsStoreKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Store Keeper').exists()


class IsStoreKeeperReadonly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Store Keeper').exists() and request.method in permissions.SAFE_METHODS


class IsProjectManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Project Manager').exists()


class IsArtisan(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Artisans').exists()


class IsArtisanReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow read-only access for artisans
        return request.user.groups.filter(name='Artisans').exists() and request.method in permissions.SAFE_METHODS