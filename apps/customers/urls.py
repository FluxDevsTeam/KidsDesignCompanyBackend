from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('customer', views.ApiCustomer, basename='customer')

urlpatterns = router.urls