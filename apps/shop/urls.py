from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('inventory-item', views.ApiInventoryItem, basename='inventory-item')
router.register('inventory-item-category', views.ApiInventoryCategory, basename='inventory_item_category')
router.register('sold', views.ApiSold, basename='sold')
router.register('add-stock', views.ApiAddStock, basename='add_stock')

urlpatterns = router.urls