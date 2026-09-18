from django.contrib.auth import logout
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_GET
from django.views.generic import FormView, TemplateView

from schedule.models import Student
from user.forms import RegisterForm
from user.models import InviteToken, ActivationToken


@require_GET
def get_invite_url(request, pk: int) -> HttpResponse:
    student = get_object_or_404(
        Student.active_objects.select_related(
            "invite_token",
        ),
        pk=pk,
    )

    if hasattr(student, "invite_token"):
        invite_token = student.invite_token
    else:
        invite_token = InviteToken.objects.create(student_profile=student)

    relative_url = reverse("user:register")

    full_invite_url = (
        f"{request.build_absolute_uri(relative_url)}?token={invite_token.id}"
    )

    return HttpResponse(full_invite_url, content_type="text/plain; charset=utf-8")


class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    next_page = reverse_lazy("user:user-menu")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["token"] = self.request.GET.get("token", "")
        return context

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        token_id = self.request.POST.get("token") or self.request.GET.get("token")

        if token_id:
            invite_token = InviteToken.objects.select_related("student_profile").get(
                id=token_id
            )
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
        context["token"] = self.request.GET.get("token", "")
        return context

    @transaction.atomic
    def form_valid(self, form):
        user = form.save()

        activation_token = ActivationToken.objects.create(user=user)

        token_id = self.request.POST.get("token") or self.request.GET.get("token")

        if token_id:
            invite_token = InviteToken.objects.select_related("student_profile").get(
                id=token_id
            )
            student = invite_token.student_profile

            student.user = user
            student.save(update_fields=["user"])

            invite_token.delete()

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
            except (ActivationToken.DoesNotExist, ValueError):
                success = False

        context["success"] = success

        return context


def logout_view(request) -> HttpResponse:
    logout(request)
    return redirect("user:login")


class UserMenuView(TemplateView):
    template_name = "accounts/menu.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["user"] = self.request.user

        return context
