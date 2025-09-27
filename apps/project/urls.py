from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from django.urls import path
from . import views

router = DefaultRouter()
router.register('project', views.ApiProject, basename='project')

project_router = NestedDefaultRouter(router, 'project', lookup='project')
project_router.register('other-production-record', views.ApiOtherProductionRecord, basename='other_production_record')

overhead_cost_view = views.OverheadCostViewSet.as_view({'get': 'list', 'patch': 'partial_update'})

urlpatterns = [
    path('overhead-cost/', overhead_cost_view, name='overhead-cost'),
    *router.urls,
    *project_router.urls,
]