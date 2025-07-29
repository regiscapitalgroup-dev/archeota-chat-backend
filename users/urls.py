from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView 
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    UserDetailView,
    LogoutView, 
    GoogleLoginView, 
    CompanyViewset, 
    ProfileDetailView, 
    RegisterView,
    ForgotMyPassword,
    PasswordResetConfirmView,
    UserViewSet, RoleViewset
)

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewset, basename='roles')
router.register(r'companies', CompanyViewset, basename='companies')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='token-obtain-pair'), 
    path('login/refresh/', TokenRefreshView.as_view(), name='token-refresh'), 
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    path('password-reset/', ForgotMyPassword.as_view(), name='password_reset'),
    path('reset-password/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('user/', UserDetailView.as_view(), name='user-detail'), 
    path('user/profile/', ProfileDetailView.as_view(), name='prfile'),
    path('', include(router.urls))
]