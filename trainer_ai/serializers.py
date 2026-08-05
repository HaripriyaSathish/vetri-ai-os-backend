from rest_framework import serializers
from .models import (
    Batch, LessonPlan, DailySchedule, Attendance, Assignment,
    MockInterviewQuestion, AssignmentSubmission, Report, MockInterviewSession, Message,
)
from .models import Holiday


class BatchSerializer(serializers.ModelSerializer):
    topics_covered = serializers.SerializerMethodField()
    students_enrolled = serializers.SerializerMethodField()
    pending_topics = serializers.SerializerMethodField()
    trainer_username = serializers.CharField(source='trainer.username', read_only=True)
    trainer_first_name = serializers.CharField(source='trainer.first_name', read_only=True)
    trainer_last_name = serializers.CharField(source='trainer.last_name', read_only=True)

    class Meta:
        model = Batch
        fields = [
            'id', 'name', 'trainer', 'trainer_username', 'trainer_first_name', 'trainer_last_name', 'start_date', 'end_date', 'status',
            'planned_topics', 'topics_covered', 'pending_topics', 'students_enrolled',
            'max_students', 'class_start_time', 'created_at',
        ]
        read_only_fields = ['trainer']

    def get_topics_covered(self, obj):
        return list(LessonPlan.objects.filter(batch=obj).values_list('topic', flat=True).distinct())

    def get_students_enrolled(self, obj):
        return (
            Attendance.objects.filter(batch=obj)
            .order_by('student_id')
            .values_list('student_id', flat=True)
            .distinct()
            .count()
        )

    def get_pending_topics(self, obj):
        if not obj.planned_topics:
            return []
        planned = [t.strip() for t in obj.planned_topics.split(',') if t.strip()]
        covered = set(LessonPlan.objects.filter(batch=obj).values_list('topic', flat=True))
        covered_lower = {c.lower() for c in covered}
        return [t for t in planned if t.lower() not in covered_lower]


class LessonPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPlan
        fields = ['id', 'batch', 'topic', 'content', 'date', 'created_at']


class DailyScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySchedule
        fields = ['id', 'batch', 'date', 'start_time', 'end_time', 'topic', 'notes', 'created_at']


class AttendanceSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'batch', 'student', 'student_username', 'date', 'status', 'marked_by', 'created_at']
        read_only_fields = ['marked_by']


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'batch', 'category', 'title', 'description', 'due_date', 'created_at']


class MockInterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockInterviewQuestion
        fields = ['id', 'batch', 'topic', 'question', 'difficulty', 'created_at']


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_first_name = serializers.CharField(source='student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='student.last_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    due_date = serializers.DateField(source='assignment.due_date', read_only=True)
    on_time = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_title', 'due_date', 'student', 'student_username',
            'student_first_name', 'student_last_name', 'score', 'remarks', 'submitted_at', 'on_time', 'verified',
        ]

    def get_on_time(self, obj):
        return obj.submitted_at.date() <= obj.assignment.due_date


class ReportSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.name', read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'batch', 'batch_name', 'title', 'content', 'generated_by', 'created_at']
        read_only_fields = ['generated_by']


class MockInterviewSessionSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = MockInterviewSession
        fields = ['id', 'batch', 'student', 'student_username', 'invited_at', 'scheduled_datetime', 'meeting_link', 'attended', 'score', 'feedback']

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_first_name = serializers.CharField(source='sender.first_name', read_only=True)
    sender_last_name = serializers.CharField(source='sender.last_name', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'batch', 'sender', 'sender_username', 'sender_first_name', 'sender_last_name',
            'recipient', 'recipient_username',
            'content', 'is_read', 'created_at', 'category', 'leave_from_date', 'leave_to_date',
        ]
        read_only_fields = ['sender']   

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'batch', 'date', 'reason']        