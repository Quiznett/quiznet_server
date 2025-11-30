 # account/middleware.py
from importlib.resources import path
import traceback
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth import get_user_model
from django.utils.functional import SimpleLazyObject

User = get_user_model()


def _refresh_cookie_kwargs(max_age_seconds=864000):
    return {
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }


def _access_cookie_kwargs(max_age_seconds=300):
    return {
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "max_age": max_age_seconds,
        "path": "/",
    }


class RefreshAccessMiddleware(MiddlewareMixin):
    """
    Middleware that tries to ensure each request has a valid access token.
    If none is present or it is expired, it attempts to use the refresh cookie to:
      - create a new access token and inject Authorization header
      - set access_token cookie on response (HttpOnly)
      - optionally rotate refresh token if SIMPLE_JWT.ROTATE_REFRESH_TOKENS=True
    """
    SKIP_PATHS = [
        "/api/v1/auth/login/",
        "/api/v1/auth/register/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/refresh/",
        "/admin/",
        "/static/",
        "/media/",
    ]

    def _should_skip(self, path: str) -> bool:
        
        return path in self.SKIP_PATHS
    
    
    
    def process_request(self, request):
        # Skip certain paths
        if request.path.startswith("/api/v1/auth/"):
            return None


        # If Authorization header already present, do nothing
        if request.META.get("HTTP_AUTHORIZATION"):
            return None

        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return None

        try:         
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)
        except TokenError:
            print("ERROR OCCURRED:", TokenError)
            traceback.print_exc()
            return None

        # Inject header for downstream authentication
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {new_access}"

        # Lazy populate request.user so views can use it
        def _get_user():
            uid = refresh.payload.get("user_id")
            try:
                return User.objects.get(id=uid) if uid else None
            except Exception:
                return None

        request.user = SimpleLazyObject(_get_user)

        # Save new tokens on request for process_response
        request._refreshed_access_token = new_access
        request._used_refresh_token = refresh
        return None

    def process_response(self, request, response):
        # If we didn't refresh, exit early
        if not getattr(request, "_refreshed_access_token", None):
            return response

        # Set access_token cookie (HttpOnly)
        access_val = request._refreshed_access_token
        # determine cookie lifetime seconds safely
        try:
            access_seconds = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        except Exception:
            access_seconds = 300

        response.set_cookie(
            key="access_token",
            value=access_val,
            httponly=True,
            **_access_cookie_kwargs(max_age_seconds=access_seconds)
        )

        # If rotation configured, rotate refresh token
        rotate = bool(settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False))
        if rotate and getattr(request, "_used_refresh_token", None):
            old_refresh = request._used_refresh_token
            try:
                old_refresh.blacklist()
            except Exception:
                pass
            try:
                uid = old_refresh.payload.get("user_id")
                if uid:
                    new_refresh = RefreshToken.for_user(User.objects.get(id=uid))
                    try:
                        refresh_seconds = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
                    except Exception:
                        refresh_seconds = 864000
                    response.set_cookie(
                        key="refresh_token",
                        value=str(new_refresh),
                        httponly=True,
                        **_refresh_cookie_kwargs(max_age_seconds=refresh_seconds)
                    )
            except Exception:
                response.delete_cookie("refresh_token", path="/")
            
            

        return response