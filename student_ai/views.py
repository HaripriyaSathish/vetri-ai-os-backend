from datetime import date

from django.db import models as dj_models
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trainer_ai.models import Attendance, Assignment, AssignmentSubmission, MockInterviewSession, Report, Message

from .models import StudentNotification
from .permissions import IsStudent, get_student_batch
from .serializers import (
    StudentAttendanceSerializer,
    StudentAssignmentSerializer,
    AssignmentSubmissionMiniSerializer,
    StudentAssessmentSerializer,
    StudentReportSerializer,
    StudentMessageSerializer,
    StudentNotificationSerializer,
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from trainer_ai.models import SubmissionAttachment
from core.email_utils import send_email
from django.http import HttpResponse
from trainer_ai.report_excel import build_zone_report_excel
from trainer_ai.views import compute_zone_rows, get_week_range, get_month_range

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        student = request.user
        batch = get_student_batch(student)

        attendance_qs = Attendance.objects.filter(student=student, batch=batch) if batch else Attendance.objects.none()
        total_days = attendance_qs.count()
        present_days = attendance_qs.filter(status="present").count()
        attendance_pct = round((present_days / total_days) * 100, 1) if total_days else None

        assignments_qs = Assignment.objects.filter(batch=batch) if batch else Assignment.objects.none()
        submitted_ids = set(
            AssignmentSubmission.objects.filter(student=student, assignment__batch=batch).values_list(
                "assignment_id", flat=True
            )
        )
        pending = [a for a in assignments_qs if a.id not in submitted_ids and a.due_date >= date.today()]
        overdue = [a for a in assignments_qs if a.id not in submitted_ids and a.due_date < date.today()]

        latest_report = Report.objects.filter(batch=batch).order_by("-created_at").first() if batch else None
        unread_notifications = StudentNotification.objects.filter(student=student, is_read=False).count()
        unread_messages = Message.objects.filter(recipient=student, is_read=False).count()

        return Response(
            {
                "batch": batch.name if batch else None,
                "trainer": batch.trainer.get_full_name() or batch.trainer.username if batch else None,
                "attendance_percent": attendance_pct,
                "pending_assignments_count": len(pending),
                "overdue_assignments_count": len(overdue),
                "unread_notifications": unread_notifications,
                "unread_messages": unread_messages,
                "latest_report": (
                    StudentReportSerializer(latest_report, context={"request": request}).data
                    if latest_report
                    else None
                ),
            }
        )


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class StudentAttendanceListView(generics.ListAPIView):
    serializer_class = StudentAttendanceSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return Attendance.objects.filter(student=self.request.user).order_by("-date")


# ---------------------------------------------------------------------------
# Assignments / Daily Tasks (category='task') / Mini & Main Projects
# ---------------------------------------------------------------------------

class StudentAssignmentListView(generics.ListAPIView):
    """
    GET /api/student/assignments/                 -> all categories
    GET /api/student/assignments/?category=task    -> Daily Tasks
    GET /api/student/assignments/?category=mini_project
    GET /api/student/assignments/?category=main_project
    """

    serializer_class = StudentAssignmentSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        batch = get_student_batch(self.request.user)
        if not batch:
            return Assignment.objects.none()
        qs = Assignment.objects.filter(batch=batch).order_by("-due_date")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class StudentAssignmentSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    MAX_FILES = 3
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file

    def post(self, request):
        assignment_id = request.data.get('assignment')
        student_note = request.data.get('student_note', '')
        links = request.data.get('links', '')
        cc_email = request.data.get('cc_email', '')
        subject = request.data.get('subject', '')
        files = request.FILES.getlist('attachments')

        if not assignment_id:
            return Response({"detail": "assignment is required."}, status=400)

        if len(files) > self.MAX_FILES:
            return Response({"detail": f"Maximum {self.MAX_FILES} attachments allowed."}, status=400)

        for f in files:
            if f.size > self.MAX_FILE_SIZE:
                return Response({"detail": f"'{f.name}' exceeds the 5MB limit per file."}, status=400)

        if not files and not links.strip() and not student_note.strip():
            return Response({"detail": "Provide at least a file, a link, or a note."}, status=400)

        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({"detail": "Assignment not found."}, status=404)

        submission, _ = AssignmentSubmission.objects.update_or_create(
            assignment=assignment,
            student=request.user,
            defaults={
                'student_note': student_note,
                'links': links,
                'cc_email': cc_email,
                'submitted_at': timezone.now(),
            },
        )

        if files:
            submission.attachments.all().delete()  # resubmission replaces old files
            for f in files:
                SubmissionAttachment.objects.create(submission=submission, file=f)

        # Email the trainer
        trainer = assignment.batch.trainer
        to_email = trainer.official_email or trainer.email
        if to_email:
            cc_list = [c.strip() for c in cc_email.split(',') if c.strip()] if cc_email else None
            full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username

            links_html = "".join(
                f"<li><a href='{l.strip()}'>{l.strip()}</a></li>" for l in links.split('\n') if l.strip()
            )
            attachment_html = "".join(
                f"<li><a href='{a.file.url}'>Attachment {i + 1}</a></li>"
                for i, a in enumerate(submission.attachments.all())
            )

            email_subject = subject or f"Submission of {assignment.title}"
            email_body = (
                f"<p><strong>Student:</strong> {full_name}</p>"
                f"<p><strong>Assignment:</strong> {assignment.title} ({assignment.get_category_display()})</p>"
                f"<p>{student_note}</p>"
                + (f"<p><strong>Links:</strong></p><ul>{links_html}</ul>" if links_html else "")
                + (f"<p><strong>Attachments:</strong></p><ul>{attachment_html}</ul>" if attachment_html else "")
            )
            send_email(to=to_email, subject=email_subject, html_body=email_body, cc=cc_list)

        return Response(
            AssignmentSubmissionMiniSerializer(submission, context={'request': request}).data,
            status=201,
        )


# ---------------------------------------------------------------------------
# Assessments (mock interviews)
# ---------------------------------------------------------------------------

class StudentAssessmentListView(generics.ListAPIView):
    serializer_class = StudentAssessmentSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return MockInterviewSession.objects.filter(student=self.request.user).order_by("-invited_at")


# ---------------------------------------------------------------------------
# Progress / Reports / personalized feedback
# ---------------------------------------------------------------------------

class StudentProgressView(generics.ListAPIView):
    """Every batch report for this student's batch, this student's note pulled out."""

    serializer_class = StudentReportSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        batch = get_student_batch(self.request.user)
        if not batch:
            return Report.objects.none()
        return Report.objects.filter(batch=batch).order_by("-created_at")


# ---------------------------------------------------------------------------
# Ask Trainer — built on trainer_ai.Message, restricted to this student's own
# conversation with their own batch's trainer. Never batchmates: the
# queryset is filtered to rows where THIS student is sender or recipient,
# so nobody else's thread is ever reachable through this endpoint.
# ---------------------------------------------------------------------------

class StudentMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentMessageSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        student = self.request.user
        return Message.objects.filter(
            dj_models.Q(sender=student) | dj_models.Q(recipient=student)
        ).order_by("created_at")


class MarkMessagesReadView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request):
        Message.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"ok": True})


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class StudentNotificationListView(generics.ListAPIView):
    serializer_class = StudentNotificationSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return StudentNotification.objects.filter(student=self.request.user)


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, pk):
        notif = get_object_or_404(StudentNotification, pk=pk, student=request.user)
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return Response({"ok": True})


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request):
        StudentNotification.objects.filter(student=request.user, is_read=False).update(is_read=True)
        return Response({"ok": True})


class StudentEligibilityView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        student = request.user
        batch = get_student_batch(student)
        if not batch:
            return Response({"detail": "Not enrolled in a batch yet."}, status=404)

        attendance_qs = Attendance.objects.filter(student=student, batch=batch)
        total_days = attendance_qs.count()
        present_days = attendance_qs.filter(status="present").count()
        attendance_pct = round((present_days / total_days) * 100, 1) if total_days else 0

        category_breakdown = []
        for cat_key, cat_label in Assignment.CATEGORY_CHOICES:
            assignments = Assignment.objects.filter(batch=batch, category=cat_key).order_by("due_date")
            rows = []
            for a in assignments:
                sub = AssignmentSubmission.objects.filter(assignment=a, student=student).first()
                on_time = bool(sub) and sub.submitted_at.date() <= a.due_date
                rows.append({
                    "id": a.id,
                    "title": a.title,
                    "due_date": a.due_date,
                    "submitted": bool(sub),
                    "submitted_at": sub.submitted_at if sub else None,
                    "on_time": on_time if sub else None,
                    "score": sub.score if sub else None,
                })
            category_breakdown.append({
                "category": cat_key,
                "label": cat_label,
                "total": assignments.count(),
                "submitted": sum(1 for r in rows if r["submitted"]),
                "rows": rows,
            })

        # Same logic as trainer_ai's get_batch_eligibility(), scoped to this student
        total_assignments = Assignment.objects.filter(batch=batch).count()
        submissions = AssignmentSubmission.objects.filter(student=student, assignment__batch=batch)
        on_time_count = sum(1 for s in submissions if s.submitted_at.date() <= s.assignment.due_date)
        all_on_time = (
            total_assignments > 0
            and submissions.count() >= total_assignments
            and on_time_count >= total_assignments
        )
        eligible = attendance_pct >= 85 and all_on_time

        session = MockInterviewSession.objects.filter(batch=batch, student=student).first()

        return Response({
            "batch_status": batch.status,
            "batch_label": f"{batch.course_name or batch.name} - {batch.start_date.strftime('%B %Y') if batch.start_date else ''}",
            "attendance_percentage": attendance_pct,
            "present_days": present_days,
            "total_days": total_days,
            "assignments_submitted": submissions.count(),
            "total_assignments": total_assignments,
            "all_on_time": all_on_time,
            "eligible": eligible,
            "category_breakdown": category_breakdown,
            "mock_interview": {
                "invited": True,
                "invited_at": session.invited_at,
                "scheduled_datetime": session.scheduled_datetime,
                "attended": session.attended,
                "score": session.score,
                "feedback": session.feedback,
            } if session else {"invited": False},
        })


from trainer_ai.models import RecordingView
from .serializers import StudentRecordingSerializer


class StudentRecordingListView(generics.ListAPIView):
    serializer_class = StudentRecordingSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return RecordingView.objects.filter(student=self.request.user).select_related('recording').order_by('-recording__date') 


class StudentZoneReportDownloadView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request, period):
        if period not in ('weekly', 'monthly'):
            return Response({"detail": "Invalid period."}, status=400)

        batch = get_student_batch(request.user)
        if not batch:
            return Response({"detail": "Not enrolled in a batch yet."}, status=404)

        start, end = get_week_range() if period == 'weekly' else get_month_range()
        rows = compute_zone_rows(batch.id, start, end)

        label = 'Weekly' if period == 'weekly' else 'Monthly'
        title = f"{batch.course_name or batch.name} - {label} Production Report ({start} to {end})"
        excel_buffer = build_zone_report_excel(rows, title)
        filename = f"{batch.name.replace(' ', '_')}_{label}_Zone_Report.xlsx"

        response = HttpResponse(
            excel_buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response       