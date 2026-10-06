from schedule.models import Student


def apply_lesson_charges(charged_before: set[int], charged_after: set[int]) -> None:
    for student in Student.objects.filter(pk__in=charged_after - charged_before):
        student.consume_lessons(1)

    for student in Student.objects.filter(pk__in=charged_before - charged_after):
        student.refund_lessons(1)
