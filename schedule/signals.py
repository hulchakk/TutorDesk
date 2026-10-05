import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from schedule.models import Lesson, GroupLesson, LessonStatusEnum, Student

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Lesson)
def handle_lesson_status_change(sender, instance: Lesson, created, **kwargs):
    if created:
        return

    previous_instance = Lesson.objects.filter(pk=instance.pk).values(
        "status"
    ).first()
    if not previous_instance:
        return

    old_status = previous_instance["status"]
    new_status = instance.status

    if old_status == new_status:
        return

    if new_status == LessonStatusEnum.FINISHED and old_status != LessonStatusEnum.CANCELED:
        instance.student.consume_lessons(1)
        logger.info("Consumed 1 lesson for student %s (individual lesson %s)", instance.student.id, instance.id)

    elif old_status == LessonStatusEnum.FINISHED and new_status != LessonStatusEnum.FINISHED:
        instance.student.consume_lessons(-1)
        logger.info(
            "Refunded 1 lesson for student %s (individual lesson %s)",
            instance.student.id,
            instance.id,
        )


@receiver(post_save, sender=GroupLesson)
def handle_group_lesson_status_change(sender, instance: GroupLesson, created, **kwargs):
    if created:
        return

    previous_instance = GroupLesson.objects.filter(pk=instance.pk).values(
        "status"
    ).first()
    if not previous_instance:
        return

    old_status = previous_instance["status"]
    new_status = instance.status

    if old_status == new_status:
        return

    if new_status == LessonStatusEnum.FINISHED and old_status != LessonStatusEnum.CANCELED:
        present_student_ids = [
            record["student_id"]
            for record in instance.attendance_list
            if record.get("status") == "present"
        ]

        for student_id in present_student_ids:
            try:
                student = Student.objects.get(pk=student_id)
                student.consume_lessons(1)
            except Student.DoesNotExist:
                logger.warning("Student %s not found for group lesson %s", student_id, instance.id)

        logger.info(
            "Consumed lessons for %d students in group lesson %s",
            len(present_student_ids),
            instance.id,
        )

    elif old_status == LessonStatusEnum.FINISHED and new_status != LessonStatusEnum.FINISHED:
        present_student_ids = [
            record["student_id"]
            for record in instance.attendance_list
            if record.get("status") == "present"
        ]

        for student_id in present_student_ids:
            try:
                student = Student.objects.get(pk=student_id)
                student.consume_lessons(-1)
            except Student.DoesNotExist:
                logger.warning("Student %s not found for group lesson %s", student_id, instance.id)

        logger.info(
            "Refunded lessons for %d students in group lesson %s",
            len(present_student_ids),
            instance.id,
        )
