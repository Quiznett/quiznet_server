from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from account.views import RegisterView,LoginView,LogoutView, TokenRefreshView
urlpatterns =[

    path("register/",RegisterView.as_view()),
    path("login/",LoginView.as_view()),
    path("logout/",LogoutView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view())

]
