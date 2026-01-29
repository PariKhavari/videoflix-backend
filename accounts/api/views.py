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
    clear_auth_cookies,
    create_activation_token,
    create_uidb64,
    make_refresh_token,
    send_activation_email,
    set_access_cookie,
    set_auth_cookies,
)


class RegisterView(APIView):
    """POST /api/register/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Bitte überprüfe deine Eingaben und versuche es erneut."}, status=400)

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
    """GET /api/activate/<uidb64>/<token>/"""
    permission_classes = [AllowAny]

    def get(self, request, uidb64: str, token: str):
        user = self._get_user(uidb64)
        if not user:
            return Response({"message": "Aktivierung fehlgeschlagen."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"message": "Aktivierung fehlgeschlagen."}, status=400)

        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"message": "Konto erfolgreich aktiviert."}, status=200)

    def _get_user(self, uidb64: str):
        """Decode uidb64 and return user or None."""
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return None


class LoginView(APIView):
    """POST /api/login/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Bitte überprüfe deine Eingaben und versuche es erneut."}, status=401)

        user = serializer.validated_data["user"]
        refresh = make_refresh_token(user)

        response = Response(
            {"detail": "Login erfolgreich", "user": {"id": user.id, "username": user.username}},
            status=200,
        )
        set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """POST /api/logout/"""
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh_token")
        if not raw_refresh:
            return Response({"detail": "Refresh-Token fehlt."}, status=400)

        if not self._blacklist_refresh(raw_refresh):
            return Response({"detail": "Refresh-Token fehlt."}, status=400)

        response = Response(
            {"detail": "Abmeldung erfolgreich! Alle Tokens werden gelöscht. Das Aktualisierungstoken ist jetzt ungültig."},
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
    """POST /api/token/refresh/"""
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh_token")
        if not raw_refresh:
            return Response({"detail": "Refresh-Token fehlt."}, status=400)

        access_token = self._create_access_token(raw_refresh)
        if not access_token:
            return Response({"detail": "Ungültiger Refresh-Token."}, status=401)

        response = Response({"detail": "Token aktualisiert", "access": access_token}, status=200)
        set_access_cookie(response, access_token)
        return response

    def _create_access_token(self, raw_refresh: str) -> str | None:
        """Return a new access token string or None."""
        try:
            refresh = RefreshToken(raw_refresh)
            return str(refresh.access_token)
        except TokenError:
            return None
