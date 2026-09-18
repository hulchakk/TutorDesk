from django.urls import path

from user.views import get_invite_url, LoginView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path(
        "student/<int:pk>/get_invite/",
        get_invite_url,
        name="get-invite",
    ),
]

app_name = "user"
