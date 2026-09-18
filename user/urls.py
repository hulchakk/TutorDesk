from django.urls import path

from user.views import get_invite_url, LoginView, RegisterView, RegisterCompleteView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path(
        "student/<int:pk>/get_invite/",
        get_invite_url,
        name="get-invite",
    ),
    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),
    path(
        "register/complete/",
        RegisterCompleteView.as_view(),
        name="register-complete",
    ),
]

app_name = "user"
