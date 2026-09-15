from decimal import Decimal

from django import forms

from schedule.models import Student, Group


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
