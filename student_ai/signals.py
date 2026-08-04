"""
Three notification triggers, all connected lazily so this doesn't blow up
if trainer_ai isn't loaded yet at import time:

1. New Assignment posted to a batch -> every student with at least one
   Attendance record in that batch gets a StudentNotification.
2. A trainer sends a Message to a student -> that student gets a
   StudentNotification (a student replying does NOT notify themself).
3. A new Report is generated for a batch -> every student in that batch
   gets a "your progress report is ready" notification.

Call `connect_all()` once from trainer_ai's AppConfig.ready() — see
TRAINER_AI_PATCHES.md for the exact one-line addition.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import StudentNotification


def _students_in_batch(batch):
    from trainer_ai.models import Attendance

    student_ids = (
        Attendance.objects.filter(batch=batch).values_list("student_id", flat=True).distinct()
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.filter(id__in=student_ids)


def connect_all():
    try:
        from trainer_ai.models import Assignment, Message, Report
    except ImportError:
        return

    @receiver(post_save, sender=Assignment)
    def notify_students_of_new_assignment(sender, instance, created, **kwargs):
        if not created:
            return
        students = _students_in_batch(instance.batch)
        StudentNotification.objects.bulk_create(
            [
                StudentNotification(
                    student=student,
                    notif_type="assignment",
                    title=f"New {instance.get_category_display()}: {instance.title}",
                    message=f"Due {instance.due_date}",
                    related_link=f"/student/assignments?highlight={instance.id}",
                )
                for student in students
            ]
        )

        # Optional: also email students via Resend, same pattern used
        # elsewhere in Vetri AI-OS (bypasses Render's blocked SMTP ports).
        #
        # import resend
        # from decouple import config
        # resend.api_key = config('RESEND_API_KEY', default='')
        # for student in students:
        #     resend.Emails.send({
        #         "from": config('RESEND_FROM_EMAIL'),
        #         "to": student.email,
        #         "subject": f"New assignment: {instance.title}",
        #         "html": f"<p>Due {instance.due_date}. Log in to your student portal to view it.</p>",
        #     })

    @receiver(post_save, sender=Message)
    def notify_student_of_trainer_message(sender, instance, created, **kwargs):
        if not created:
            return
        # Only notify when the TRAINER is the one who sent it.
        if getattr(instance.sender, "role", None) != "trainer":
            return
        StudentNotification.objects.create(
            student=instance.recipient,
            notif_type="message",
            title="New message from your trainer",
            message=instance.content[:200],
            related_link="/student/ask-trainer",
        )

    @receiver(post_save, sender=Report)
    def notify_students_of_new_report(sender, instance, created, **kwargs):
        if not created:
            return
        students = _students_in_batch(instance.batch)
        StudentNotification.objects.bulk_create(
            [
                StudentNotification(
                    student=student,
                    notif_type="report",
                    title="Your progress report is ready",
                    message=instance.title,
                    related_link="/student/progress",
                )
                for student in students
            ]
        )


connect_all()
