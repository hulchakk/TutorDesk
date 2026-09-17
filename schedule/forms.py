from datetime import timedelta
from decimal import Decimal

from django import forms
from django.db.models import Q

from schedule.models import Student, Group, Lesson, GroupLesson


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
    duration = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 1,
            }
        )
    )

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

        self.initial["duration"] = 60

        if self.instance and self.instance.pk and self.instance.duration:
            if isinstance(self.instance.duration, timedelta):
                self.initial["duration"] = int(
                    self.instance.duration.total_seconds() // 60
                )

        if user and "student" in self.fields:
            queryset = Student.active_objects.filter(teacher=user)

            if self.instance and self.instance.pk and self.instance.student_id:
                queryset = Student.objects.filter(
                    Q(teacher=user)
                    & (Q(is_active=True) | Q(pk=self.instance.student_id))
                )

            self.fields["student"].queryset = queryset

    def clean_duration(self):
        duration = self.cleaned_data.get("duration", 0)

        if duration <= 0:
            raise forms.ValidationError("Lesson duration must be greater than 0.")

        return timedelta(minutes=duration)


class GroupLessonForm(LessonForm):
    class Meta:
        model = GroupLesson
        fields = ["start_datetime", "duration", "group", "status"]
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                }
            ),
            "group": forms.Select(
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
        super().__init__(*args, user=user, **kwargs)

        if user and "group" in self.fields:
            queryset = Group.active_objects.filter(teacher=user)

            if self.instance and self.instance.pk and self.instance.group_id:
                queryset = Group.objects.filter(
                    Q(teacher=user) & (Q(is_active=True) | Q(pk=self.instance.group_id))
                )

            self.fields["group"].queryset = queryset
