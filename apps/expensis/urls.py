from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('expense', views.ApiExpense, basename='expense')
router.register('expense-category', views.ApiExpenseCategory, basename='expense_category')
router.register('assets', views.ApiAssets, basename='assets')

urlpatterns = router.urls