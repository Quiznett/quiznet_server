# views.py
import os
import json
import urllib.parse


from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from account.serializers import RegisterSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
# ------------------------------
# OTP SYSTEM
# ------------------------------

from django.core.mail import send_mail
import random
from datetime import timedelta
from django.utils import timezone
from .models import EmailOTP

class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email required"}, status=400)

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already registered. Please login instead."},
                status=400
            )

        # generate OTP
        otp = str(random.randint(100000, 999999))

        # update/create OTP entry
        EmailOTP.objects.update_or_create(email=email, defaults={"otp": otp})

        # send mail
        send_mail(
            subject="Your OTP Code",
            message=f"Your OTP is {otp}. It will expire in 5 minutes.",
            from_email=os.environ.get("EMAIL_HOST_USER"),
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent successfully"})



class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        try:
            otp_obj = EmailOTP.objects.get(email=email)
        except EmailOTP.DoesNotExist:
            return Response({"error": "OTP not found"}, status=400)

        # Expired?
        if otp_obj.is_expired():
            otp_obj.delete()
            return Response({"error": "OTP expired"}, status=400)

        # Match?
        if otp_obj.otp != otp:
            return Response({"error": "Invalid OTP"}, status=400)

        # Success → delete OTP
        otp_obj.delete()
        return Response({"message": "OTP verified"}, status=200)




# ------------------------------
# COOKIE HELPERS
# ------------------------------

def _refresh_cookie_kwargs(max_age_seconds=864000):
    return {
        "secure": False ,
        "samesite": "None" if not settings.DEBUG else "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }

def _access_cookie_kwargs(max_age_seconds=300):
    return {
        "secure": False ,
        "samesite": "None" if not settings.DEBUG else "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }

def _user_cookie_kwargs(max_age_seconds=864000):
    return {
        "secure": False ,
        "samesite": "None" if not settings.DEBUG else "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }
# ------------------------------
# JSON ENCODING HELPER
# ------------------------------

def _encode_user_cookie(user_obj):
    """
    Converts user info dict → JSON string → URL-encoded string.
    This ensures cookie is safe even if it contains spaces, quotes, special chars.
    """
    json_str = json.dumps(user_obj, separators=(",", ":"))
    return urllib.parse.quote(json_str, safe="")


def _user_info(user: User):
    """
    Returns a minimal dictionary describing the user.
    Stored inside the readable cookie for frontend convenience.
    """
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "fullname": f"{user.first_name} {user.last_name}".strip(),
    }


# ------------------------------
# REGISTER VIEW
# ------------------------------

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Creates a new user, returns access token in body,
        and sets both access + refresh tokens as cookies.
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Successful response
        resp = Response({
            "message": "User registered successfully!",
            "access": access_token,
            "user": _user_info(user)
        }, status=status.HTTP_201_CREATED)

        # Set refresh token (HttpOnly)
        resp.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,                       # ensure HttpOnly
            **_refresh_cookie_kwargs(max_age_seconds=864000)
        )

        # Set access token (HttpOnly)
        resp.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,                       # ensure HttpOnly
            **_access_cookie_kwargs(max_age_seconds=300)
        )

        # Set readable user cookie (NOT HttpOnly)
        resp.set_cookie(
            key="user",
            value=_encode_user_cookie(_user_info(user)),
            **_user_cookie_kwargs(max_age_seconds=864000)
        )

        return resp



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Authenticates user, returns JWT tokens,
        sets cookies same as registration.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Django auth system
        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Successful response
        resp = Response({
            "message": "User logged in successfully!",
            "access": access_token,
            "user": _user_info(user)
        }, status=status.HTTP_200_OK)

                # Set refresh cookie (HttpOnly)
        resp.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,                       # ensure HttpOnly
            **_refresh_cookie_kwargs(max_age_seconds=864000)
        )

        # Set readable user cookie (NOT HttpOnly)
        resp.set_cookie(
            key="user",
            value=_encode_user_cookie(_user_info(user)),
            **_user_cookie_kwargs(max_age_seconds=864000)
        )

        # Set access token cookie (HttpOnly)
        resp.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,                       # ensure HttpOnly
            **_access_cookie_kwargs(max_age_seconds=300)
        )


        return resp


# ------------------------------
# LOGOUT VIEW
# ------------------------------

class LogoutView(APIView):
    """
    Deletes refresh + access + user cookies.
    Blacklists refresh token IF token_blacklist app is installed.
    """
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        resp = Response({"message": "Logged out"}, status=status.HTTP_200_OK)

        # Try blacklisting the refresh token
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)

                # If blacklist app is installed
                try:
                    token.blacklist()
                except Exception:
                    # Silently ignore if blacklist is not enabled
                    pass

            except TokenError:
                pass

        # Delete all cookies
        resp.delete_cookie("refresh_token", path='/')
        resp.delete_cookie("access_token", path='/')
        resp.delete_cookie("user", path='/')

        return resp