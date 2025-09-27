from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from django.urls import path
from . import views

router = DefaultRouter()
router.register('salary-workers', views.ApiSalaryWorkers, basename='salary-workers')
router.register('contractors', views.ApiContractors, basename='contractors')
router.register('paid', views.ApiPaid, basename='paid')

salary_router = NestedDefaultRouter(router, 'salary-workers', lookup='salary_worker')
salary_router.register('record', views.ApiSalaryWorkersRecord, basename='Salary_worker_record')

contractor_router = NestedDefaultRouter(router, 'contractors', lookup='contractor')
contractor_router.register('record', views.ApiContractorRecord, basename='contractors_record')

urlpatterns = [
    path('contractors/<int:pk>/details/', views.ContractorDetailViewSet.as_view({'get': 'details'}), name='contractor-detail'),
    path('salary-workers/<int:pk>/details/', views.SalaryWorkerDetailViewSet.as_view({'get': 'details'}), name='salaryworker-detail'),
    *router.urls,
    *salary_router.urls,
    *contractor_router.urls,
]