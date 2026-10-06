from django.db import transaction
from django.db.models import QuerySet
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from schedule.models import GroupLesson, Lesson
from schedule.services import apply_lesson_charges


@receiver(pre_save, sender=Lesson)
@receiver(pre_save, sender=GroupLesson)
def remember_charged_students(sender, instance, raw=False, **kwargs):
    previous = None

    if instance.pk and not raw:
        previous = sender.objects.filter(pk=instance.pk).first()

    instance._charged_before = previous.charged_student_ids() if previous else set()


@receiver(post_save, sender=Lesson)
@receiver(post_save, sender=GroupLesson)
def sync_charges_on_save(sender, instance, raw=False, **kwargs):
    if raw:
        return

    with transaction.atomic():
        apply_lesson_charges(
            getattr(instance, "_charged_before", set()),
            instance.charged_student_ids(),
        )


@receiver(post_delete, sender=Lesson)
@receiver(post_delete, sender=GroupLesson)
def refund_charges_on_delete(sender, instance, origin=None, **kwargs):
    if isinstance(origin, QuerySet):
        if origin.model is not sender:
            return
    elif origin is not None and origin is not instance:
        return

    with transaction.atomic():
        apply_lesson_charges(instance.charged_student_ids(), set())
