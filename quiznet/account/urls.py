from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from account.views import RegisterView,LoginView,LogoutView, SendOTPView, VerifyOTPView
urlpatterns =[

    path("register/",RegisterView.as_view()),
    path("login/",LoginView.as_view()),
    path("logout/",LogoutView.as_view()),
    path("send-otp/", SendOTPView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),

]