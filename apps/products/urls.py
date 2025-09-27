from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from . import views

router = DefaultRouter()
router.register('product', views.ApiProduct, basename='product')

product_router = NestedDefaultRouter(router, 'product', lookup='product')
product_router.register('contractor', views.ApiProductContractor, basename='product_contractor')
product_router.register('salary', views.ApiProductSalaryWorker, basename='product_salary')
product_router.register('raw-materials-used', views.ApiRawMaterialUsed, basename='raw-materials-used')
product_router.register('quotation', views.ApiQuotation, basename='quotation')

urlpatterns = [
    *router.urls,
    *product_router.urls,
]
