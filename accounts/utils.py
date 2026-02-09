from __future__ import annotations
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.template.loader import render_to_string

def create_activation_token(user) -> str:
    """Create activation token for a user."""
    return default_token_generator.make_token(user)


def create_uidb64(user) -> str:
    """Create base64 user id for URLs."""
    return urlsafe_base64_encode(force_bytes(user.pk))


def _frontend_base_url() -> str:
    """Return frontend base URL."""
    return getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5500").rstrip("/")


def build_frontend_activation_link(uidb64: str, token: str) -> str:
    """
    Build activation link pointing to the frontend page.

    Expected format:
    http://localhost:5500/pages/auth/activate.html?uid={uid}&token={token}
    """
    base = _frontend_base_url()
    return f"{base}/pages/auth/activate.html?uid={uidb64}&token={token}"


def build_frontend_password_reset_link(uidb64: str, token: str) -> str:
    """Build password reset link pointing to the frontend."""
    base = _frontend_base_url()
    return f"{base}/pages/auth/password_reset.html?uid={uidb64}&token={token}"


def send_activation_email(to_email: str, activation_link: str) -> None:
    """Send activation email using Django's send_mail()."""
    subject = "Activate your Videoflix account"
    html_message = render_to_string(
        "accounts/activation_email.html",
        {"activation_link": activation_link},
    )

    send_mail(
        subject=subject,
        message="", 
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[to_email],
        fail_silently=False,
        html_message=html_message,
    )


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """Send password reset email with a frontend link."""
    subject = "Reset your Videoflix password"
    html = render_to_string("accounts/password_reset_email.html", {"reset_link": reset_link})
    msg = EmailMultiAlternatives(subject=subject, to=[to_email])
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


def make_refresh_token(user) -> RefreshToken:
    """Create refresh token for a user."""
    return RefreshToken.for_user(user)


def _cookie_common_kwargs() -> dict:
    """Return common cookie settings."""
    return {
        "httponly": True,
        "secure": getattr(settings, "AUTH_COOKIE_SECURE", False),
        "samesite": getattr(settings, "AUTH_COOKIE_SAMESITE", "Lax"),
        "path": "/",
    }


def set_auth_cookies(response: Response, refresh: RefreshToken) -> None:
    """Set HttpOnly cookies for access and refresh tokens."""
    response.set_cookie(
        "access_token",
        str(refresh.access_token),
        max_age=int(getattr(settings, "ACCESS_COOKIE_MAX_AGE", 60 * 5)),
        **_cookie_common_kwargs(),
    )
    response.set_cookie(
        "refresh_token",
        str(refresh),
        max_age=int(getattr(settings, "REFRESH_COOKIE_MAX_AGE", 60 * 60 * 24 * 7)),
        **_cookie_common_kwargs(),
    )


def set_access_cookie(response: Response, access_token: str) -> None:
    """Set only the access token cookie."""
    response.set_cookie(
        "access_token",
        access_token,
        max_age=int(getattr(settings, "ACCESS_COOKIE_MAX_AGE", 60 * 5)),
        **_cookie_common_kwargs(),
    )


def clear_auth_cookies(response: Response) -> None:
    """Delete auth cookies."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
