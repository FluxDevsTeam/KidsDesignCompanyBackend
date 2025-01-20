from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('sold', views.ApiSold, basename='sold')
router.register('salary-workers', views.ApiSalaryWorkers, basename='salary-workers')
router.register('contractors', views.ApiContractors, basename='contractors')
router.register('quotation', views.ApiQuotation, basename='quotation')
router.register('removed', views.ApiRemoved, basename='removed')
router.register('product', views.ApiProduct, basename='product')
router.register('project', views.ApiProject, basename='project')
router.register('raw-materials', views.ApiRawMaterial, basename='raw-materials')
router.register('raw-materials-used', views.ApiRawMaterialUsed, basename='raw-materials-used')
router.register('expense', views.ApiExpense, basename='expense')
router.register('inventory-item', views.ApiInventoryItem, basename='inventory-item')
router.register('customer', views.ApiCustomer, basename='customer')


urlpatterns = [
    path("", include(router.urls)),
    path('sold/sell/', views.ApiSold.as_view({'post': 'sell'}), name='sell'),
    path('sold/edit/', views.ApiSold.as_view({'put': 'edit', 'patch': 'edit'}), name='edit'),
    path('sold/delete/', views.ApiSold.as_view({'delete': 'delete'}), name='delete'),

]

