from django.urls import path

from user.views import (
    get_invite_url,
    LoginView,
    RegisterView,
    RegisterCompleteView,
    ActivateUserView,
    logout_view,
    UserMenuView,
    change_password_view,
    reset_password_request_view,
    reset_password_complete_view,
)

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
    path(
        "activate_account/",
        ActivateUserView.as_view(),
        name="activate-user",
    ),
    path(
        "logout/",
        logout_view,
        name="logout",
    ),
    path(
        "menu/",
        UserMenuView.as_view(),
        name="user-menu",
    ),
    path(
        "change_password/",
        change_password_view,
        name="change-password",
    ),
    path(
        "reset_password_request/",
        reset_password_request_view,
        name="reset-password-request",
    ),
    path(
        "reset_password_complete/",
        reset_password_complete_view,
        name="reset-password-complete",
    ),
]

app_name = "user"
