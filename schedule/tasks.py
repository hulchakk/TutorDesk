import logging

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from schedule.models import GroupLesson, Lesson, LessonStatusEnum
from schedule.services import apply_lesson_charges

logger = logging.getLogger(__name__)


def finish_past_lessons(model) -> int:
    lesson_ids = list(
        model.objects.alias(end_datetime=F("start_datetime") + F("duration"))
        .filter(status=LessonStatusEnum.PLANNED, end_datetime__lt=timezone.now())
        .values_list("pk", flat=True)
    )

    finished_count = 0

    for lesson_id in lesson_ids:
        with transaction.atomic():
            lesson = (
                model.objects.select_for_update()
                .filter(pk=lesson_id, status=LessonStatusEnum.PLANNED)
                .first()
            )

            if not lesson:
                continue

            lesson.status = LessonStatusEnum.FINISHED
            apply_lesson_charges(set(), lesson.charged_student_ids())
            model.objects.filter(pk=lesson_id).update(status=LessonStatusEnum.FINISHED)
            finished_count += 1

    return finished_count


@shared_task
def consume_completed_lessons() -> dict:
    result = {
        "individual": finish_past_lessons(Lesson),
        "group": finish_past_lessons(GroupLesson),
    }

    logger.info(
        "Finished lessons: %d individual, %d group",
        result["individual"],
        result["group"],
    )

    return result
