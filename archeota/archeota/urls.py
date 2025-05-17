from django.contrib import admin
from django.urls import path, include, re_path
from accounts.views import GoogleLogin, GoogleLoginCallback, LoginPage
from chat.views import ChatAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("login/", LoginPage.as_view(), name="login"),
    path("api/v1/auth/", include("dj_rest_auth.urls")),
    re_path(r"^api/v1/auth/accounts/", include("allauth.urls")),
    path("api/v1/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/v1/auth/google/", GoogleLogin.as_view(), name="google_login"),
    path("api/v1/auth/google/callback/", GoogleLoginCallback.as_view(), name="google_login_callback"),
    path('api/v1/chat/', ChatAPIView.as_view(), name='chat_api')
]