from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .dashboard_views import ApiStorekeeper, ApiAdminDashboard, ApiFactoryManagerDashboard, CEODashboardViewSet, ApiShopkeeper
from .views import StoreQuotation

router = DefaultRouter()
router.register('sold', views.ApiSold, basename='sold')
router.register('salary-workers', views.ApiSalaryWorkers, basename='salary-workers')
router.register('contractors', views.ApiContractors, basename='contractors')
router.register('paid', views.ApiPaid, basename='paid')
router.register('removed', views.ApiRemoved, basename='removed')
router.register('product', views.ApiProduct, basename='product')
router.register('project', views.ApiProject, basename='project')
router.register('raw-materials', views.ApiRawMaterial, basename='raw-materials')
router.register('expense', views.ApiExpense, basename='expense')
router.register('expense-category', views.ApiExpenseCategory, basename='expense_category')
router.register('inventory-item', views.ApiInventoryItem, basename='inventory-item')
router.register('inventory-item-category', views.ApiInventoryCategory, basename='inventory_item_category')
router.register('raw-materials-category', views.ApiStoreCategory, basename='raw_materials_category')
router.register('customer', views.ApiCustomer, basename='customer')
router.register('assets', views.ApiAssets, basename='assets')
router.register('add-raw-materials', views.ApiAddRawMaterials, basename='add_raw_material')
router.register('add-stock', views.ApiAddStock, basename='add_stock')

product_router = NestedDefaultRouter(router, 'product', lookup='product')
product_router.register('contractor', views.ApiProductContractor, basename='product_contractor')
product_router.register('salary', views.ApiProductSalaryWorker, basename='product_salary')
product_router.register('raw-materials-used', views.ApiRawMaterialUsed, basename='raw-materials-used')
product_router.register('quotation', views.ApiQuotation, basename='quotation')

salary_router = NestedDefaultRouter(router, 'salary-workers', lookup='salary_worker')
salary_router.register('record', views.ApiSalaryWorkersRecord, basename='Salary_worker_record')

contractor_router = NestedDefaultRouter(router, 'contractors', lookup='contractor')
contractor_router.register('record', views.ApiContractorRecord, basename='contractors_record')

project_router = NestedDefaultRouter(router, 'project', lookup='project')
project_router.register('other-production-record', views.ApiOtherProductionRecord, basename='other_production_record')

overhead_cost_view = views.OverheadCostViewSet.as_view({'get': 'list', 'patch': 'partial_update'})


urlpatterns = [
    path("", include(router.urls)),
    path("", include(product_router.urls)),
    path("", include(salary_router.urls)),
    path("", include(contractor_router.urls)),
    path("", include(project_router.urls)),
    # path('view-added-stock/', views.ApiAddStock.as_view({'get': 'list'}), name='view_added_stock'),
    # path('add-stock/', views.ApiAddStock.as_view({'post': 'create'}), name='add_stock'),
    # path('view-added-raw-materials/', views.ApiAddRawMaterials.as_view({'get': 'list'}), name='view_added_raw_materials'),
    # path('add-raw-materials/', views.ApiAddRawMaterials.as_view({'post': 'create'}), name='add_raw_materials'),
    path('overhead-cost/', overhead_cost_view, name='overhead-cost'),

    #     ############ dashboard #####################
    path('all-quotation/', StoreQuotation.as_view({'get': 'list'})),
    path('storekeeper-dashboard/', ApiStorekeeper.as_view({'get': 'list'})),
    path('shopkeeper-dashboard/', ApiShopkeeper.as_view({'get': 'list'})),
    # path('workers-dashboard/', WorkersDashboardViewSet.as_view({'get': 'list'})),
    path('admin-dashboard/', ApiAdminDashboard.as_view({'get': 'list'})),
    path('factory-manager-dashboard/', ApiFactoryManagerDashboard.as_view({'get': 'list'})),
    path('ceo-dashboard/', CEODashboardViewSet.as_view({'get': 'list'}))
]
