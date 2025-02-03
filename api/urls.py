from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter


router = DefaultRouter()
router.register('sold', views.ApiSold, basename='sold')
router.register('salary-workers', views.ApiSalaryWorkers, basename='salary-workers')
router.register('contractors', views.ApiContractors, basename='contractors')
router.register('removed', views.ApiRemoved, basename='removed')
router.register('product', views.ApiProduct, basename='product')
router.register('project', views.ApiProject, basename='project')
router.register('raw-materials', views.ApiRawMaterial, basename='raw-materials')
router.register('expense', views.ApiExpense, basename='expense')
router.register('expense-category', views.ApiExpenseCategory, basename='expense_category')
router.register('inventory-item', views.ApiInventoryItem, basename='inventory-item')
router.register('inventory-item-category', views.ApiInventoryCategory, basename='inventory_item_category')
router.register('store-category', views.ApiStoreCategory, basename='store_category')
router.register('customer', views.ApiCustomer, basename='customer')

product_router = NestedDefaultRouter(router, 'product', lookup='product')
product_router.register('contractor', views.ApiProductContractor, basename='product_contractor')
product_router.register('salary', views.ApiProductSalaryWorker, basename='product_salary')
product_router.register('raw-materials-used', views.ApiRawMaterialUsed, basename='raw-materials-used')
product_router.register('quotation', views.ApiQuotation, basename='quotation')

urlpatterns = [
    path("", include(router.urls)),
    path("", include(product_router.urls)),
]

