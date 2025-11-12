# views.py
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


# Helper to build cookie kwargs for refresh token (HttpOnly)
def _refresh_cookie_kwargs(max_age_seconds=864000):
    return {
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "max_age": max_age_seconds,
        "path": "/",  # you can scope to '/api/token/refresh/' if desired
    }

# Helper to build cookie kwargs for readable user cookie
def _user_cookie_kwargs(max_age_seconds=864000):
    return {
        "httponly": False,          # allow frontend JS to read it
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }

# Helper to produce a safe JSON string for cookie value (URL-encoded)
def _encode_user_cookie(user_obj):
    """
    user_obj: dict
    returns: URL-encoded JSON string safe for cookie value
    """
    json_str = json.dumps(user_obj, separators=(",", ":"))  # compact
    return urllib.parse.quote(json_str, safe="")  # encode so no special chars break cookie


# Helper to prepare minimal user info dict
def _user_info(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "fullname": f"{user.first_name} {user.last_name}".strip(),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        resp = Response({
            "message": "User registered successfully!",
            "access": access_token,
            "user": _user_info(user)
        }, status=status.HTTP_201_CREATED)

        # set refresh token cookie (HttpOnly)
        resp.set_cookie(
            key="refresh_token",
            value=refresh_token,
            **_refresh_cookie_kwargs(max_age_seconds=864000)  # 10 days
        )

        # set readable user cookie (URL-encoded JSON)
        resp.set_cookie(
            key="user",
            value=_encode_user_cookie(_user_info(user)),
            **_user_cookie_kwargs(max_age_seconds=864000)
        )

        return resp


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        resp = Response({
            "message": "User logged in successfully!",
            "access": access_token,
            "user": _user_info(user)
        }, status=status.HTTP_200_OK)

        # set refresh token cookie (HttpOnly)
        resp.set_cookie(
            key="refresh_token",
            value=refresh_token,
            **_refresh_cookie_kwargs(max_age_seconds=864000)  # 10 days
        )

        # set readable user cookie (URL-encoded JSON)
        resp.set_cookie(
            key="user",
            value=_encode_user_cookie(_user_info(user)),
            **_user_cookie_kwargs(max_age_seconds=864000)
        )

        return resp


class TokenRefreshView(APIView):
    """
    POST -> reads refresh token from HttpOnly cookie 'refresh_token' and returns a new access token.
    Also updates the 'user' cookie with fresh user data (useful if user details changed).
    Frontend must call this endpoint with fetch(..., credentials: 'include')
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({"detail": "Refresh token not found."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            # Attempt to get user id from token payload and refresh user cookie
            user_obj = None
            user_id = None
            # SimpleJWT uses 'user_id' claim by default
            try:
                user_id = refresh.payload.get("user_id") or refresh.get("user_id", None)
            except Exception:
                # fallback: try direct payload access
                user_id = refresh.payload.get("user_id") if hasattr(refresh, "payload") else None

            if user_id is not None:
                try:
                    user = User.objects.get(id=user_id)
                    user_obj = _user_info(user)
                except User.DoesNotExist:
                    user_obj = None

            resp = Response({"access": new_access}, status=status.HTTP_200_OK)

            # Optionally: rotate refresh token here and set new cookie (left out for simplicity).
            # Keep refresh cookie unchanged unless you implement rotation.

            # Update user cookie if we could fetch user info
            if user_obj:
                resp.set_cookie(
                    key="user",
                    value=_encode_user_cookie(user_obj),
                    **_user_cookie_kwargs(max_age_seconds=864000)
                )

            return resp

        except TokenError:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """
    POST -> blacklist the refresh token (if present) and delete both cookies.
    Frontend must call with credentials: 'include'
    """
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        resp = Response({"message": "Logged out"}, status=status.HTTP_200_OK)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                # Blacklist if token_blacklist app installed
                try:
                    token.blacklist()
                except Exception:
                    # token_blacklist may not be installed; ignore if so
                    pass
            except TokenError:
                pass

        # Delete cookies (path should match set_cookie path)
        resp.delete_cookie("refresh_token", path='/')
        resp.delete_cookie("user", path='/')

        return resp
