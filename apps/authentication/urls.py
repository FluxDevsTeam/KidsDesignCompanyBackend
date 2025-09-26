from django.urls import path,include
from .views import (UserSignupViewSet, UserLoginViewSet, GroupViewSet)
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('roles', GroupViewSet, basename='role')
router.register('signup', UserSignupViewSet, basename='user_signup')


urlpatterns = [
    path('', include(router.urls)),
    path('login/', UserLoginViewSet.as_view({'post': 'create'}), name='UserLoginViewSet'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
