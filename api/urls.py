from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('route', views.ApiSold, basename='route')
router.register('cities', views.ApiSalaryWorkers, basename='cities')
router.register('pending', views.ApiContractors, basename='pending')
router.register('booking', views.ApiQuotation, basename='booking')
router.register('booking', views.ApiRemoved, basename='booking')
router.register('booking', views.ApiProduct, basename='booking')
router.register('booking', views.ApiProject, basename='booking')
router.register('booking', views.ApiRawMaterial, basename='booking')
router.register('booking', views.ApiRawMaterialUsed, basename='booking')
router.register('booking', views.ApiListField, basename='booking')
router.register('booking', views.ApiExpense, basename='booking')
router.register('booking', views.ApiRemoved, basename='booking')
router.register('booking', views.ApiRemoved, basename='booking')
router.register('booking', views.ApiRemoved, basename='booking')


urlpatterns = [
    path("", include(router.urls)),
]

