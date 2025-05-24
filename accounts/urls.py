from django.urls import path
from .views import UserRegistrationView, GoogleLogin, GoogleLoginCallback
from rest_framework_simplejwt.views import (
    TokenObtainPairView, 
    TokenRefreshView,    
    TokenBlacklistView,   
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('google/', GoogleLogin.as_view(), name='google_login'),
    path('google/callback/', GoogleLoginCallback.as_view(), name='google_login_callback'),

]
