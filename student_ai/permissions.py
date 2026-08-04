from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    message = "This endpoint is only available to student accounts."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "student"
        )


def get_student_batch(user):
    """
    Your Batch model has no `students` field — enrollment is tracked
    implicitly the same way BatchStudentsView / get_batch_eligibility do it
    in trainer_ai/views.py: the distinct set of Attendance rows for that
    student. A student's very first Attendance record (created by
    EnrollStudentView / BulkEnrollStudentsView at enrollment time) is what
    ties them to a batch, so this mirrors that pattern exactly.
    """
    from trainer_ai.models import Attendance

    record = Attendance.objects.filter(student=user).order_by("-date").first()
    return record.batch if record else None
