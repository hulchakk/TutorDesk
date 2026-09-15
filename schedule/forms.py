from datetime import timedelta
from decimal import Decimal

from django import forms

from schedule.models import Student, Group, Lesson


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["name", "lessons_price"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Student Name",
                }
            ),
            "lessons_price": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Lessons price"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)
        self.fields["lessons_price"].initial = Decimal("600.00")


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Group Name",
                }
            )
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["start_datetime", "duration", "student", "status"]
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                }
            ),
            "duration": forms.NumberInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "student": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["duration"].initial = 60

        if user:
            self.fields["student"].queryset = Student.active_objects.filter(
                teacher=user
            )

    def clean_duration(self):
        duration = self.cleaned_data.get("duration", timedelta(seconds=0))
        if duration <= timedelta(seconds=0):
            raise forms.ValidationError("Lesson duration must be greater than 0.")
        return duration
