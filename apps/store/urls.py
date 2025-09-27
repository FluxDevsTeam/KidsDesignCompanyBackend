from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('raw-materials', views.ApiRawMaterial, basename='raw-materials')
router.register('removed', views.ApiRemoved, basename='removed')
router.register('raw-materials-category', views.ApiStoreCategory, basename='raw_materials_category')
router.register('add-raw-materials', views.ApiAddRawMaterials, basename='add_raw_material')

urlpatterns = router.urls