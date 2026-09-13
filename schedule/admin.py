from django.contrib import admin

from schedule.models import Student, Lesson, Group, GroupLesson

admin.site.register(Student)
admin.site.register(Lesson)
admin.site.register(Group)
admin.site.register(GroupLesson)
