import json

from rest_framework import serializers

from trainer_ai.models import (
    Attendance,
    Assignment,
    AssignmentSubmission,
    SubmissionAttachment,
    MockInterviewSession,
    Report,
    Message,
)

from .models import StudentNotification


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class StudentAttendanceSerializer(serializers.ModelSerializer):
    batch_label = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["id", "batch", "batch_label", "date", "status", "created_at"]

    def get_batch_label(self, obj):
        batch = obj.batch
        name = batch.course_name or batch.name
        month = batch.start_date.strftime("%B %Y") if batch.start_date else ""
        return f"{name} - {month}" if month else name

# ---------------------------------------------------------------------------
# Assignments / Daily Tasks (category='task') / Mini & Main Projects
# ---------------------------------------------------------------------------

class SubmissionAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionAttachment
        fields = ["id", "url"]

    def get_url(self, obj):
        return obj.file.url if obj.file else None


class AssignmentSubmissionMiniSerializer(serializers.ModelSerializer):
    on_time = serializers.SerializerMethodField()
    attachments = SubmissionAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = ["id", "submitted_at", "score", "remarks", "student_note", "links", "attachments", "on_time", "verified"]

    def get_on_time(self, obj):
        return obj.submitted_at.date() <= obj.assignment.due_date


class StudentAssignmentSerializer(serializers.ModelSerializer):
    my_submission = serializers.SerializerMethodField()
    trainer_submission_email = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ["id", "batch", "category", "title", "description", "due_date", "created_at", "my_submission", "trainer_submission_email"]

    def get_my_submission(self, obj):
        student = self.context["request"].user
        submission = AssignmentSubmission.objects.filter(assignment=obj, student=student).first()
        return AssignmentSubmissionMiniSerializer(submission, context=self.context).data if submission else None

    def get_trainer_submission_email(self, obj):
        trainer = obj.batch.trainer
        return trainer.official_email or trainer.email or None


# ---------------------------------------------------------------------------
# Assessments (mock interviews)
# ---------------------------------------------------------------------------

class StudentAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockInterviewSession
        fields = ["id", "batch", "invited_at", "scheduled_datetime", "attended", "score", "feedback"]


# ---------------------------------------------------------------------------
# Progress / personalized feedback
#
# Report is batch-level (not per-student): `content` is a JSON string shaped
# like {"executive_summary": ..., "recommendations": [...], "student_notes":
# [{"student": "username", "note": "..."}]}. We surface the whole report
# (for context) plus this student's own note pulled out specifically.
# ---------------------------------------------------------------------------

class StudentReportSerializer(serializers.ModelSerializer):
    my_note = serializers.SerializerMethodField()
    executive_summary = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "batch", "title", "executive_summary", "my_note", "created_at"]

    def _parsed_content(self, obj):
        try:
            return json.loads(obj.content)
        except (ValueError, TypeError):
            return {}

    def get_executive_summary(self, obj):
        return self._parsed_content(obj).get("executive_summary")

    def get_my_note(self, obj):
        student = self.context["request"].user
        for entry in self._parsed_content(obj).get("student_notes", []):
            if entry.get("student") == student.username:
                return entry.get("note")
        return None


# ---------------------------------------------------------------------------
# Ask Trainer — reuses trainer_ai.Message as-is. `category` /
# `leave_from_date` / `leave_to_date` only work if you've applied the patch
# in TRAINER_AI_PATCHES.md; they're written defensively so this still runs
# without it (everything just behaves as a plain message).
# ---------------------------------------------------------------------------

class StudentMessageSerializer(serializers.ModelSerializer):
    is_mine = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True, default="")

    class Meta:
        model = Message
        fields = [
            "id",
            "batch",
            "sender",
            "sender_name",
            "recipient",
            "is_mine",
            "content",
            "is_read",
            "created_at",
            "category",
            "leave_from_date",
            "leave_to_date",
        ]
        read_only_fields = ["id", "batch", "sender", "sender_name", "recipient", "is_mine", "is_read", "created_at"]

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.sender_id == request.user.id)

    def create(self, validated_data):
        from .permissions import get_student_batch

        request = self.context["request"]
        student = request.user
        batch = get_student_batch(student)
        validated_data["sender"] = student
        validated_data["batch"] = batch
        validated_data["recipient"] = batch.trainer if batch else None
        return super().create(validated_data)


class StudentNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentNotification
        fields = ["id", "notif_type", "title", "message", "related_link", "is_read", "created_at"]
        read_only_fields = fields


from trainer_ai.models import RecordingView


class StudentRecordingSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='recording.id')
    title = serializers.CharField(source='recording.title')
    date = serializers.DateField(source='recording.date')
    notes = serializers.CharField(source='recording.notes', allow_null=True)
    watched = serializers.BooleanField(source='clicked')
    watched_at = serializers.DateTimeField(source='clicked_at', allow_null=True)
    tracked_link = serializers.SerializerMethodField()

    def get_tracked_link(self, obj):
        request = self.context['request']
        base_url = request.build_absolute_uri('/').rstrip('/')
        return f"{base_url}/api/trainer/recordings/track/{obj.token}/"        