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


# ------------------------------
# COOKIE HELPERS
# ------------------------------

def _refresh_cookie_kwargs(max_age_seconds=864000):
    """
    Returns kwargs for the REFRESH TOKEN cookie.
    - HttpOnly so JS cannot access it
    - Secure when DEBUG=False
    - SameSite=Lax for safe cross-site behaviour
    - max_age = 10 days (default)
    """
    return {
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }


def _user_cookie_kwargs(max_age_seconds=864000):
    """
    Returns kwargs for USER cookie.
    - Readable by JS (httponly=False)
    - Stores user info for frontend use.
    - Same lifetime as refresh token.
    """
    return {
        "httponly": False,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }


def _access_cookie_kwargs(max_age_seconds=300):
    """
    Returns kwargs for ACCESS TOKEN cookie.
    - HttpOnly so JS cannot access it
    - Very short lifetime (default 5 minutes)
    """
    return {
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
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
            **_refresh_cookie_kwargs(max_age_seconds=864000)
        )

        # Set access token (HttpOnly)
        resp.set_cookie(
            key="access_token",
            value=access_token,
            **_access_cookie_kwargs(max_age_seconds=300)
        )

        # Set readable user cookie
        resp.set_cookie(
            key="user",
            value=_encode_user_cookie(_user_info(user)),
            **_user_cookie_kwargs(max_age_seconds=864000)
        )

        return resp


# ------------------------------
# LOGIN VIEW
# ------------------------------

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

        # Set refresh cookie
        resp.set_cookie(
            key="refresh_token",
            value=refresh_token,
            **_refresh_cookie_kwargs(max_age_seconds=864000)
        )

        # Set readable user cookie
        resp.set_cookie(
            key="user",
            value=_encode_user_cookie(_user_info(user)),
            **_user_cookie_kwargs(max_age_seconds=864000)
        )

        # Set access token cookie
        resp.set_cookie(
            key="access_token",
            value=access_token,
            **_access_cookie_kwargs(max_age_seconds=300)
        )

        return resp


# ------------------------------
# TOKEN REFRESH VIEW
# ------------------------------

class TokenRefreshView(APIView):
    """
    Refreshes access token using refresh token stored in HttpOnly cookie.
    Frontend must use: fetch(url, { method:"POST", credentials:"include" })
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Read refresh token from cookie
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response({"detail": "Refresh token not found."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # Validate & decode refresh token
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            # Attempt to read user ID from token
            try:
                user_id = refresh.payload.get("user_id")
            except Exception:
                user_id = None

            user_obj = None
            if user_id:
                # Update readable user cookie with fresh DB values
                try:
                    user = User.objects.get(id=user_id)
                    user_obj = _user_info(user)
                except User.DoesNotExist:
                    pass

            # Successful response
            resp = Response({"access": new_access}, status=status.HTTP_200_OK)

            # Update access cookie
            resp.set_cookie(
                key="access_token",
                value=new_access,
                **_access_cookie_kwargs(max_age_seconds=300)
            )

            # Optionally update user cookie
            if user_obj:
                resp.set_cookie(
                    key="user",
                    value=_encode_user_cookie(user_obj),
                    **_user_cookie_kwargs(max_age_seconds=864000)
                )

            return resp

        except TokenError:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)


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
