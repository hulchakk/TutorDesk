from django.urls import path

from payments.views import StudentProfilesListView

urlpatterns = [
    path("my_profiles/", StudentProfilesListView.as_view(), name="student-profiles"),
]

app_name = "payments"
