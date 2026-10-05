import logging

from celery import shared_task
from django.db import models, transaction
from django.utils import timezone

from schedule.models import Lesson, GroupLesson, LessonStatusEnum, Student

logger = logging.getLogger(__name__)


@shared_task
def consume_completed_lessons() -> dict:
    now = timezone.now()

    with transaction.atomic():
        completed_individual = Lesson.objects.select_related("student").filter(
            status=LessonStatusEnum.PLANNED,
            start_datetime__lt=now,
        )

        individual_count = 0
        for lesson in completed_individual:
            lesson.student.consume_lessons(1)
            lesson.status = LessonStatusEnum.FINISHED
            lesson.save(update_fields=["status", "updated_at"])
            individual_count += 1

        completed_group = GroupLesson.objects.filter(
            status=LessonStatusEnum.PLANNED,
            start_datetime__lt=now,
        )

        group_count = 0
        present_student_ids = set()

        for group_lesson in completed_group:
            for record in group_lesson.attendance_list:
                if record.get("status") == "present":
                    present_student_ids.add(record["student_id"])

            group_lesson.status = LessonStatusEnum.FINISHED
            group_lesson.save(update_fields=["status", "updated_at"])
            group_count += 1

        for student_id in present_student_ids:
            try:
                student = Student.objects.get(pk=student_id)
                student.consume_lessons(1)
            except Student.DoesNotExist:
                logger.warning("Student %s not found", student_id)

    logger.info(
        "Consumed lessons: %d individual, %d group attendees",
        individual_count,
        len(present_student_ids),
    )
    return {"individual": individual_count, "group_attendees": len(present_student_ids)}
