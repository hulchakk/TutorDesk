from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET

from schedule.models import Student
from user.models import InviteToken


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

    relative_url = reverse("user:accept-invite")

    full_invite_url = (
        f"{request.build_absolute_uri(relative_url)}?token={invite_token.id}"
    )

    return HttpResponse(full_invite_url, content_type="text/plain; charset=utf-8")
