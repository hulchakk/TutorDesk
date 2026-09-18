from django.contrib.auth.views import LoginView
from django.urls import path

from user.views import get_invite_url

urlpatterns = [
    path(
        "login/", LoginView.as_view(template_name="accounts/login.html"), name="login"
    ),
    path(
        "student/<int:pk>/get_invite/",
        get_invite_url,
        name="get-invite",
    ),
]

app_name = "user"
