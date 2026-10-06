from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_GET
from django.views.generic import FormView, TemplateView

from schedule.models import Student
from services.notifications.email import EmailNotificationsService
from services.notifications.exceptions import NotificationError
from user.decorators import teacher_required
from user.forms import RegisterForm, ChangePasswordForm, ResetPasswordForm
from user.models import InviteToken, ActivationToken, ResetPasswordToken


def find_invite_token(token_id: str | None) -> InviteToken | None:
    """A used, expired or malformed invite link must not break login or registration."""
    if not token_id:
        return None
    try:
        return (
            InviteToken.objects.select_related("student_profile")
            .filter(id=token_id, student_profile__user__isnull=True)
            .first()
        )
    except ValidationError:
        return None


@teacher_required
@require_GET
def get_invite_url(request, pk: int) -> HttpResponse:
    student = get_object_or_404(
        Student.active_objects.select_related(
            "invite_token",
        ),
        Q(teacher=request.user) | Q(group__teacher=request.user),
        pk=pk,
        user__isnull=True,
    )

    if hasattr(student, "invite_token"):
        invite_token = student.invite_token
    else:
        invite_token = InviteToken.objects.create(student_profile=student)

    # Login page links to registration and keeps the token, so it fits both new and existing users.
    relative_url = reverse("user:login")

    full_invite_url = (
        f"{request.build_absolute_uri(relative_url)}?token={invite_token.id}"
    )

    return HttpResponse(full_invite_url, content_type="text/plain; charset=utf-8")


class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    next_page = reverse_lazy("user:user-menu")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # POST keeps the token when the form is re-rendered with errors
        context["token"] = self.request.POST.get("token") or self.request.GET.get(
            "token", ""
        )
        return context

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        token_id = self.request.POST.get("token") or self.request.GET.get("token")

        invite_token = find_invite_token(token_id)

        if invite_token:
            student = invite_token.student_profile

            student.user = self.request.user
            student.save(update_fields=["user"])

            invite_token.delete()

        return response


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("user:register-complete")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # POST keeps the token when the form is re-rendered with errors
        context["token"] = self.request.POST.get("token") or self.request.GET.get(
            "token", ""
        )
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                user = form.save()

                activation_token = ActivationToken.objects.create(user=user)

                token_id = self.request.POST.get("token") or self.request.GET.get(
                    "token"
                )

                invite_token = find_invite_token(token_id)

                if invite_token:
                    student = invite_token.student_profile

                    student.user = user
                    student.save(update_fields=["user"])

                    invite_token.delete()

                activation_link = self.request.build_absolute_uri(
                    f"{reverse('user:activate-user')}?token={activation_token.id}"
                )
                EmailNotificationsService().send_activation_email(
                    user.email, user.name, activation_link
                )
        except NotificationError:
            form.add_error(
                None, "We couldn't send the activation email. Please try again later."
            )
            return self.form_invalid(form)

        return super().form_valid(form)


class RegisterCompleteView(TemplateView):
    template_name = "accounts/register_complete.html"


class ActivateUserView(TemplateView):
    template_name = "accounts/activate_user.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        token_id = self.request.GET.get("token")

        success = False

        if token_id:
            try:
                with transaction.atomic():
                    token = ActivationToken.objects.select_related("user").get(
                        id=token_id
                    )
                    user = token.user
                    user.is_active = True
                    user.save(update_fields=["is_active"])
                    token.delete()
                    success = True
            except (ActivationToken.DoesNotExist, ValueError, ValidationError):
                success = False

        context["success"] = success

        return context


def logout_view(request) -> HttpResponse:
    logout(request)
    return redirect("user:login")


class UserMenuView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/menu.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["user"] = self.request.user

        return context


@login_required
def change_password_view(request):
    if request.method == "POST":
        form = ChangePasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed")
            return redirect("user:user-menu")
    else:
        form = ChangePasswordForm(user=request.user)

    return render(request, "accounts/change_password.html", {"form": form})


def reset_password_request_view(request) -> HttpResponse:
    if request.method == "POST":
        User = get_user_model()

        email = request.POST.get("email")
        try:
            user = User.objects.select_related("reset_password_token").get(email=email)
        except (User.DoesNotExist, ValueError):
            return render(
                request,
                template_name="accounts/reset_password/requested_successfully.html",
            )

        reset_password_token = getattr(user, "reset_password_token", None)

        if reset_password_token:
            if reset_password_token.is_expired:
                reset_password_token.delete()
            else:
                return render(
                    request,
                    template_name="accounts/reset_password/already_requested.html",
                )

        reset_link_base = request.build_absolute_uri(
            reverse("user:reset-password-complete")
        )

        try:
            with transaction.atomic():
                reset_password_token = ResetPasswordToken.objects.create(user=user)
                EmailNotificationsService().send_password_reset_email(
                    user.email,
                    user.name,
                    f"{reset_link_base}?token={reset_password_token.id}",
                )
        except NotificationError:
            messages.error(
                request, "We couldn't send the reset link. Please try again later."
            )
            return render(request, "accounts/reset_password/request.html")

        return render(
            request,
            template_name="accounts/reset_password/requested_successfully.html",
        )

    return render(request, "accounts/reset_password/request.html")


def reset_password_complete_view(request) -> HttpResponse:
    token_id = request.GET.get("token") or request.POST.get("token")

    try:
        if not token_id:
            raise ValueError("Token ID missing.")

        token = ResetPasswordToken.objects.select_related("user").get(id=token_id)

        if token.is_expired:
            token.delete()
            raise ValueError("Token expired.")

    except (ResetPasswordToken.DoesNotExist, ValueError, ValidationError):
        return render(
            request,
            template_name="accounts/reset_password/failed.html",
        )

    if request.method == "POST":
        form = ResetPasswordForm(user=token.user, data=request.POST)
        if form.is_valid():
            form.save()
            token.delete()
            return render(
                request,
                template_name="accounts/reset_password/successful.html",
            )
    else:
        form = ResetPasswordForm(user=token.user)

    return render(
        request,
        template_name="accounts/reset_password/complete.html",
        context={
            "form": form,
            "token": token_id,
        },
    )
