from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class RegisterForm(forms.ModelForm):
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={"placeholder": "Full name", "autocomplete": "name"}
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"placeholder": "you@example.com", "autocomplete": "email"}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Password", "autocomplete": "new-password"}
        ),
        required=True,
    )
    repeat_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Repeat password", "autocomplete": "new-password"}
        ),
        required=True,
    )

    class Meta:
        model = User
        fields = ("name", "email", "password")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        repeat_password = cleaned_data.get("repeat_password")

        if password and repeat_password and password != repeat_password:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.name = self.cleaned_data["name"]
        user.set_password(self.cleaned_data["password"])
        user.is_student = True
        user.is_active = False

        if commit:
            user.save()

        return user


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "New password", "autocomplete": "new-password"}
        ),
    )
    repeat_new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Repeat new password", "autocomplete": "new-password"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password")

        validate_password(password=new_password, user=self.user)

        return new_password

    def clean_repeat_new_password(self):
        new_password = self.cleaned_data.get("new_password")
        repeat_new_password = self.cleaned_data.get("repeat_new_password")

        if new_password != repeat_new_password:
            raise forms.ValidationError("Passwords do not match.")

        return repeat_new_password

    def save(self, request=None):
        new_password = self.cleaned_data["new_password"]

        self.user.set_password(new_password)
        self.user.save()

        return self.user


class ChangePasswordForm(ResetPasswordForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Current password",
                "autocomplete": "current-password",
            }
        ),
    )

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")

        if self.user and not self.user.check_password(old_password):
            raise forms.ValidationError("Incorrect old password.")

        return old_password
