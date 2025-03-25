from rest_framework import permissions


class CheckUserRoles(permissions.BasePermission):
    """
    Checks if a user has the necessary roles to access a view.
    """
    message = "You don't have the necessary roles to access this view"

    def has_permission(self, request, view):
        # Superuser has unrestricted access
        if request.user and request.user.is_superuser:
            return True

        # Get user roles
        user_roles = request.user.groups.values_list("name", flat=True)

        # Get required roles from the view or default to an empty list
        required_roles = getattr(view, "required_roles", [])

        # Check if there's an intersection between user roles and required roles
        return bool(set(user_roles) & set(required_roles))


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


class IsStoreKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Store Keeper').exists()


class IsStoreKeeperReadonly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Store Keeper').exists() and request.method in permissions.SAFE_METHODS


class IsProjectManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Project Manager').exists()


class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Manager').exists()


class IsArtisan(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Artisans').exists()


class IsArtisanReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow read-only access for artisans
        return request.user.groups.filter(name='Artisans').exists() and request.method in permissions.SAFE_METHODS