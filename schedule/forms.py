from datetime import timedelta

from django import forms
from django.db.models import Q

from schedule.models import Student, Group, Lesson, GroupLesson
from subscriptions.models import TariffPlan


class StudentForm(forms.ModelForm):
    available_tariffs = forms.ModelMultipleChoiceField(
        queryset=TariffPlan.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Student
        fields = ["name", "available_tariffs"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "Student name", "autocomplete": "off"}
            )
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)

        if teacher:
            self.fields["available_tariffs"].queryset = TariffPlan.objects.filter(
                teachers=teacher,
                is_active=True,
            )
        else:
            self.fields["available_tariffs"].queryset = TariffPlan.objects.filter(
                is_active=True
            )

        if self.instance and self.instance.pk:
            self.fields["available_tariffs"].initial = (
                self.instance.available_tariffs.values_list("id", flat=True)
            )

    def _save_tariffs(self, student):
        selected_tariffs = self.cleaned_data.get("available_tariffs", [])
        student.available_tariffs.set(selected_tariffs)

    def save(self, commit=True):
        student = super().save(commit=commit)

        if commit:
            self._save_tariffs(student)
        else:

            def save_m2m():
                self._save_tariffs(student)

            self.save_m2m = save_m2m

        return student


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
                # datetime-local inputs only accept the "T"-separated ISO format
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
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
            self.fields["student"].empty_label = "Select a student"

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
                # datetime-local inputs only accept the "T"-separated ISO format
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
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
            self.fields["group"].empty_label = "Select a group"
