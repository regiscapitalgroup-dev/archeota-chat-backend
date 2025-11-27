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
    UserViewSet,
    RoleViewset,
    ClassificationViewSet,
    CountriesListView,
    UserActivationView,
    AssignmentViewSet
)

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewset, basename='roles')
router.register(r'companies', CompanyViewset, basename='companies')
router.register(r'catalog/classifications', ClassificationViewSet, basename='clasificaciones')
router.register(r'assignment', AssignmentViewSet, basename='assignment')

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
    path('catalog/countries/', CountriesListView.as_view(), name='countries-list'),
    path('activate/', UserActivationView.as_view(), name='user-activate'),
    path('', include(router.urls))
]