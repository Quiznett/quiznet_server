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
    Returns kwargs for REFRESH TOKEN cookie.
    HttpOnly will be passed manually at set_cookie().
    """
    return {
        "secure": not settings.DEBUG,
       "samesite": "None" if not settings.DEBUG else "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }


def _user_cookie_kwargs(max_age_seconds=864000):
    """
    Returns kwargs for USER cookie.
    - User cookie is readable by JS (NOT HttpOnly)
    """
    return {
        "secure": not settings.DEBUG,
       "samesite": "None",
       "secure": True,
        "max_age": max_age_seconds,
        "path": "/",
    }


def _access_cookie_kwargs(max_age_seconds=300):
    """
    Returns kwargs for ACCESS TOKEN cookie.
    HttpOnly will be passed manually at set_cookie().
    """
    return {
        "secure": not settings.DEBUG,
       "samesite": "None" if not settings.DEBUG else "Lax",
       "secure": True,
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
# TOKEN REFRESH VIEW
# ------------------------------

# quiz/middleware/token_refresh.py
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.exceptions import InvalidToken
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils.functional import SimpleLazyObject

User = get_user_model()


def _refresh_cookie_kwargs(max_age_seconds=864000):
    return {
        "secure": not settings.DEBUG,
       "samesite": "None" if not settings.DEBUG else "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }


def _access_cookie_kwargs(max_age_seconds=300):
    return {
        "secure": not settings.DEBUG,
       "samesite": "None" if not settings.DEBUG else "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }


class RefreshAccessMiddleware(MiddlewareMixin):
    """
    Middleware that ensures every request has a valid access token.
    If access is missing/expired, try to refresh it using the refresh token cookie.

    Behavior:
      - Skips paths in SKIP_PATHS (login/refresh/logout/static/media)
      - If refresh succeeds: injects HTTP_AUTHORIZATION header 'Bearer <access>' into request.META
        and sets 'access_token' (HttpOnly) cookie in the response.
      - If rotation enabled: blacklists old refresh and sets new refresh cookie.
      - If refresh fails: leaves request unchanged (views will handle auth failure).
    """

    # Add any API paths you want to skip (login, logout, refresh, docs, static files)
    SKIP_PATHS = [
        "/api/v1/auth/login/",
        "/api/v1/auth/register/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/refresh/",  # avoid recursion
        "/admin/",
        "/static/",
        "/media/",
    ]

    def _should_skip(self, path: str) -> bool:
        for p in self.SKIP_PATHS:
            if path.startswith(p):
                return True
        return False

    def process_request(self, request):
        """
        Called on each request before view logic.
        If there's already an Authorization header with a valid access token, do nothing.
        Otherwise, attempt to refresh using refresh_token cookie.
        """
        path = request.path
        if self._should_skip(path):
            return None

        # If Authorization header present, assume client provided valid access token (let auth classes validate it)
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header:
            return None

        # No Authorization header - try to refresh using refresh_token cookie
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return None

        try:
            refresh = RefreshToken(refresh_token)
            # build new access token
            new_access = str(refresh.access_token)
        except TokenError:
            # Refresh invalid/expired - nothing we can do here; views will return 401
            return None

        # Inject Authorization header so DRF authentication picks it up
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {new_access}"

        # Also attach a lazy user object (optional) so views that check request.user see it immediately
        def _get_user():
            user_id = refresh.payload.get("user_id")
            try:
                return User.objects.get(id=user_id) if user_id else None
            except Exception:
                return None

        request.user = SimpleLazyObject(_get_user)

        # Save the new access token onto the request so process_response can set cookie
        request._refreshed_access_token = new_access
        # Save the refresh token used in case we need to rotate it
        request._used_refresh_token = refresh

        return None

    def process_response(self, request, response):
        """
        If we created a new access token during process_request, set the access_token cookie on response.
        If ROTATE_REFRESH_TOKENS=True, also rotate refresh token and set new refresh cookie.
        """
        # If middleware didn't refresh anything, do nothing
        if not getattr(request, "_refreshed_access_token", None):
            return response

        # Set new access_token cookie (HttpOnly)
        access_val = request._refreshed_access_token
        response.set_cookie(
            key="access_token",
            value=access_val,
            httponly=True,
            **_access_cookie_kwargs(max_age_seconds=getattr(settings, "ACCESS_TOKEN_LIFETIME_SECONDS", 300))
        )

        # Handle rotation if enabled
        rotate = getattr(settings, "SIMPLE_JWT", {}).get("ROTATE_REFRESH_TOKENS", False)
        if rotate and getattr(request, "_used_refresh_token", None):
            old_refresh = request._used_refresh_token
            # Blacklist the old refresh token if possible
            try:
                old_refresh.blacklist()
            except Exception:
                # blacklist may fail if app not installed; ignore
                pass

            # Issue a new refresh token (for the same user) and set cookie
            try:
                user_id = old_refresh.payload.get("user_id")
                if user_id:
                    new_refresh = RefreshToken.for_user(User.objects.get(id=user_id))
                    response.set_cookie(
                        key="refresh_token",
                        value=str(new_refresh),
                        httponly=True,
                        **_refresh_cookie_kwargs(max_age_seconds=getattr(settings, "REFRESH_TOKEN_LIFETIME_SECONDS", 864000))
                    )
            except Exception:
                # If something fails, delete refresh cookie to be safe
                response.delete_cookie("refresh_token", path="/")

        return response


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
