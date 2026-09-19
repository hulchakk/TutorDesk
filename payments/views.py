from django.views.generic import ListView


class StudentProfilesListView(ListView):
    template_name = "payments/student_profiles_list.html"
    context_object_name = "profiles"

    def get_queryset(self):
        return self.request.user.student_profiles.select_related(
            "teacher",
            "group",
        )
