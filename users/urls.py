from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView 
from rest_framework.routers import DefaultRouter
from .views import (
    UserCreateView,
    LoginView,
    UserDetailView,
    LogoutView, 
    GoogleLoginView, 
    RoleViewset, 
    CompanyViewset, 
    ProfileDetailView
)

router = DefaultRouter()

router.register(r'roles', RoleViewset, basename='roles')
router.register(r'companies', CompanyViewset, basename='companies')

urlpatterns = [
    path('register/', UserCreateView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='token-obtain-pair'), 
    path('login/refresh/', TokenRefreshView.as_view(), name='token-refresh'), 
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    path('user/', UserDetailView.as_view(), name='user-detail'), 
    path('user/profile/', ProfileDetailView.as_view(), name='prfile'),
    path('', include(router.urls))
]