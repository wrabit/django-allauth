from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

from allauth.account import app_settings, signals
from allauth.account.adapter import get_adapter
from allauth.account.internal.flows import email_verification_by_code
from allauth.account.internal.flows.login import perform_login
from allauth.account.models import Login
from allauth.core.internal.httpkit import get_frontend_url
from allauth.utils import build_absolute_uri


def prevent_enumeration(request: HttpRequest, email: str) -> HttpResponse:
    adapter = get_adapter(request)
    adapter.send_account_already_exists_mail(email)
    adapter.add_message(
        request,
        messages.INFO,
        "account/messages/email_confirmation_sent.txt",
        {"email": email, "login": False, "signup": True},
    )
    if app_settings.EMAIL_VERIFICATION_BY_CODE_ENABLED:
        email_verification_by_code.EmailVerificationProcess.initiate(
            request=request, user=None, email=email
        )
    resp = adapter.respond_email_verification_sent(request, None)
    return resp


def send_unknown_account_mail(request: HttpRequest, email: str) -> None:
    if not app_settings.EMAIL_UNKNOWN_ACCOUNTS:
        return None
    signup_url = get_signup_url(request)
    context = {
        "request": request,
        "signup_url": signup_url,
    }
    get_adapter().send_mail("account/email/unknown_account", email, context)


def get_signup_url(request: HttpRequest) -> str:
    url = get_frontend_url(request, "account_signup")
    if not url:
        url = build_absolute_uri(request, reverse("account_signup"))
    return url


def complete_signup(
    request,
    *,
    user,
    email_verification=None,
    redirect_url=None,
    signal_kwargs=None,
    by_passkey=False,
):
    if signal_kwargs is None:
        signal_kwargs = {}
    signals.user_signed_up.send(
        sender=user.__class__, request=request, user=user, **signal_kwargs
    )
    login = Login(
        user=user,
        email_verification=email_verification,
        redirect_url=redirect_url,
        signal_kwargs=signal_kwargs,
        signup=True,
    )
    if by_passkey:
        login.state["passkey_signup"] = True
    return perform_login(request, login)
