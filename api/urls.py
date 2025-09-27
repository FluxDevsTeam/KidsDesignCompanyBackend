from django.urls import path, include
from .dashboard_views import (
    ApiStorekeeper, ApiAdminDashboard, ApiFactoryManagerDashboard,
    CEODashboardViewSet, ApiShopkeeper, ProjectManagerDashboardViewSet,
    ApiAccountantDashboard
)

urlpatterns = [
    # Include all app URLs while preserving the same URL structure
    path("", include("apps.shop.urls")),
    path("", include("apps.store.urls")),
    path("", include("apps.workers.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.products.urls")),
    path("", include("apps.project.urls")),
    path("", include("apps.expensis.urls")),
    path("", include("apps.income.urls")),

    # Dashboard URLs
    path('storekeeper-dashboard/', ApiStorekeeper.as_view({'get': 'list'})),
    path('shopkeeper-dashboard/', ApiShopkeeper.as_view({'get': 'list'})),
    path('project-manager-dashboard/', ProjectManagerDashboardViewSet.as_view({'get': 'list'})),
    path('admin-dashboard/', ApiAdminDashboard.as_view({'get': 'list'})),
    path('accountant-dashboard/', ApiAccountantDashboard.as_view({'get': 'list'})),
    path('factory-manager-dashboard/', ApiFactoryManagerDashboard.as_view({'get': 'list'})),
    path('ceo-dashboard/', CEODashboardViewSet.as_view({'get': 'list'})),
]
