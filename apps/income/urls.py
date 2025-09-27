from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('income', views.IncomeApi, basename='income')
router.register('income-category', views.IncomeCategoryApi, basename='income_category')
router.register('balance-switch', views.BalanceSwitchApi, basename='balance_switch')

urlpatterns = router.urls