from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.api.serializers import LoginSerializer, RegisterSerializer
from accounts.utils import (
    build_frontend_activation_link,
    build_frontend_password_reset_link,
    clear_auth_cookies,
    create_activation_token,
    create_uidb64,
    make_refresh_token,
    send_activation_email,
    send_password_reset_email,
    set_access_cookie,
    set_auth_cookies,
)


class RegisterView(APIView):
    """Handle user registration and send account activation email."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Create a new inactive user and send an activation link via email."""
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Please check your input and try again."}, status=400)

        user = serializer.save()
        uidb64 = create_uidb64(user)
        token = create_activation_token(user)

        activation_link = build_frontend_activation_link(uidb64, token)
        send_activation_email(user.email, activation_link)

        return Response(
            {"user": {"id": user.id, "email": user.email}, "token": token},
            status=status.HTTP_201_CREATED,
        )
 

class ActivateView(APIView):
    """Activate a user account using uid and token from email."""
    permission_classes = [AllowAny]

    def get(self, request, uidb64: str | None = None, token: str | None = None):
        """Validate activation token and activate the user account."""
        uidb64, token = self._resolve_params(request, uidb64, token)
        if not uidb64 or not token:
            return Response({"detail": "The activation link is invalid or has expired."}
, status=400)

        user = self._get_user(uidb64)
        if not user:
            return Response({"detail": "The activation link is invalid or has expired."}
, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "The activation link is invalid or has expired."}
, status=400)

        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"detail": "Account successfully activated."}, status=200)

    def _resolve_params(self, request, uidb64: str | None, token: str | None) -> tuple[str | None, str | None]:
        """Resolve uid/token from path params first, then query params."""
        if uidb64 and token:
            return uidb64, token
        q_uid = (request.query_params.get("uid") or "").strip()
        q_token = (request.query_params.get("token") or "").strip()
        return (q_uid or None), (q_token or None)

    def _get_user(self, uidb64: str):
        """Decode uidb64 and return user or None."""
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return None


class LoginView(APIView):
    """Authenticate user and issue JWT tokens as HttpOnly cookies."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate credentials and set access and refresh tokens in cookies."""
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Please check your input and try again."}, status=401)

        user = serializer.validated_data["user"]
        refresh = make_refresh_token(user)

        response = Response(
            {"detail": "Invalid credentials.", "user": {"id": user.id, "username": user.username}},
            status=200,
        )
        set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """Logout user and invalidate refresh token."""
    permission_classes = [AllowAny]

    def post(self, request):   
        """Blacklist refresh token and delete authentication cookies."""
        raw_refresh = request.COOKIES.get("refresh_token")
        if not raw_refresh:
            return Response({"detail": "Refresh-Token failed."}, status=400)

        if not self._blacklist_refresh(raw_refresh):
            return Response({"detail": "Refresh-Token failed."}, status=400)

        response = Response(
            {"detail": "Logout completed. All tokens have been cleared."},
            status=200,
        )
        clear_auth_cookies(response)
        return response

    def _blacklist_refresh(self, raw_refresh: str) -> bool:
        """Blacklist refresh token. Returns True on success."""
        try:
            token = RefreshToken(raw_refresh)
            token.blacklist()
            return True
        except TokenError:
            return False


class TokenRefreshView(APIView):
    """Refresh expired access token using valid refresh token."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Generate a new access token and update HttpOnly cookie."""
        raw_refresh = request.COOKIES.get("refresh_token")
        if not raw_refresh:
            return Response({"detail": "Refresh-Token failed."}, status=400)

        access_token = self._create_access_token(raw_refresh)
        if not access_token:
            return Response({"detail": "invalid Refresh-Token."}, status=401)

        response = Response({"detail": "Token updated", "access": access_token}, status=200)
        set_access_cookie(response, access_token)
        return response

    def _create_access_token(self, raw_refresh: str) -> str | None:
        """Return a new access token string or None."""
        try:
            refresh = RefreshToken(raw_refresh)
            return str(refresh.access_token)
        except TokenError:
            return None


class PasswordResetView(APIView):
    """Send password reset email to user if account exists."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate token and set new password for the user."""
        email = self._get_email(request.data)
        user = self._get_active_user_by_email(email)
        if user:
            self._send_reset(user)

        return Response(
            {"detail": "Es wurde eine E-Mail zum Zurücksetzen Ihres Passworts gesendet."},
            status=200,
        )

    def _get_email(self, data) -> str:
        """Extract email string from request data."""
        value = (data.get("email") or "").strip().lower()
        return value

    def _get_active_user_by_email(self, email: str):
        """Return active user by email or None."""
        if not email:
            return None
        return User.objects.filter(email__iexact=email, is_active=True).first()

    def _send_reset(self, user) -> None:
        """Send password reset email for a user."""
        uidb64 = create_uidb64(user)
        token = default_token_generator.make_token(user)
        reset_link = build_frontend_password_reset_link(uidb64, token)
        send_password_reset_email(user.email, reset_link)


class PasswordConfirmView(APIView):
    """POST /api/password_confirm/<uidb64>/<token>/"""
    permission_classes = [AllowAny]

    def post(self, request, uidb64: str, token: str):
        user = self._get_user(uidb64)
        if not user:
            return Response({"detail": "The activation link is invalid or has expired."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "The activation link is invalid or has expired."}, status=400)

        password = self._get_new_password(request.data)
        if not password:
            return Response({"detail": "Please check your input and try again."}, status=400)

        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Your password has been successfully reset."}, status=200)

    def _get_user(self, uidb64: str):
        """Decode uidb64 and return user or None."""
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return None

    def _get_new_password(self, data) -> str | None:
        """Validate and return new password or None."""
        new_password = (data.get("new_password") or "").strip()
        confirm_password = (data.get("confirm_password") or "").strip()
        if not new_password or new_password != confirm_password:
            return None
        if len(new_password) < 8:
            return None
        return new_password