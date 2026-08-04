from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import BulkEnrollStudentsView
from .views import (
    BatchViewSet, LessonPlanViewSet, DailyScheduleViewSet, AttendanceViewSet,
    AssignmentViewSet, MockInterviewQuestionViewSet, AssignmentSubmissionViewSet,
    ReportViewSet, MockInterviewSessionViewSet, MessageViewSet,
    SendMockInviteView, MockEligibilityView, ScheduleIndividualInterviewView,
    BatchStudentsView, BatchLessonTimelineView, BatchTrainingLogView,
    BatchZoneReportView, BatchFullZoneReportView, StudentProfileView,
    UploadMockScoresView, EnrollStudentView, BulkEnrollStudentsView,
    UnreadMessageCountView, MarkMessagesReadView,
    SendWelcomeEmailView, NotifyTrainerView,
    AbsentStudentsView, NotifyAbsentStudentsView,
    ClassRecordingListCreateView, ShareRecordingView, RecordingClickTrackView, RecordingStatsView,
    BatchEnrollmentStatusView, MarkDiscontinuedView, ReactivateStudentView,EmailZoneReportView,
)
from .ai_views import (
    GenerateLessonPlanView, GenerateAssignmentView, GenerateMockQuestionsView,
    GenerateStudentProgressView, GenerateBatchPerformanceView, GenerateReportView,
)
from .views import MessageViewSet, UnreadMessageCountView, MarkMessagesReadView
router = DefaultRouter()
router.register('batches', BatchViewSet, basename='batch')
router.register('lesson-plans', LessonPlanViewSet, basename='lesson-plan')
router.register('schedules', DailyScheduleViewSet, basename='schedule')
router.register('attendance', AttendanceViewSet, basename='attendance')
router.register('assignments', AssignmentViewSet, basename='assignment')
router.register('mock-questions', MockInterviewQuestionViewSet, basename='mock-question')
router.register('submissions', AssignmentSubmissionViewSet, basename='submission')
router.register('reports', ReportViewSet, basename='report')
router.register('mock-sessions', MockInterviewSessionViewSet, basename='mock-session')
router.register('messages', MessageViewSet, basename='message')

urlpatterns = [
    # Custom paths FIRST, so they're matched before the router's generic <pk> patterns
    path('unread-message-count/', UnreadMessageCountView.as_view(), name='unread-message-count'),
    path('mark-messages-read/', MarkMessagesReadView.as_view(), name='mark-messages-read'),
    path('bulk-enroll-students/', BulkEnrollStudentsView.as_view(), name='bulk-enroll-students'),
    path('enroll-student/', EnrollStudentView.as_view(), name='enroll-student'),
    path('mock-sessions/upload-scores/', UploadMockScoresView.as_view(), name='upload-mock-scores'),
    path('ai/generate-lesson-plan/', GenerateLessonPlanView.as_view(), name='generate-lesson-plan'),
    path('ai/generate-assignment/', GenerateAssignmentView.as_view(), name='generate-assignment'),
    path('ai/generate-mock-questions/', GenerateMockQuestionsView.as_view(), name='generate-mock-questions'),
    path('ai/generate-student-progress/', GenerateStudentProgressView.as_view(), name='generate-student-progress'),
    path('ai/generate-batch-performance/', GenerateBatchPerformanceView.as_view(), name='generate-batch-performance'),
    path('ai/generate-report/', GenerateReportView.as_view(), name='generate-report'),
    path('batches/<int:batch_id>/students/', BatchStudentsView.as_view(), name='batch-students'),
    path('send-welcome-email/', SendWelcomeEmailView.as_view(), name='send-welcome-email'),
    path('notify-trainer/', NotifyTrainerView.as_view(), name='notify-trainer'),
    path('batches/<int:batch_id>/timeline/', BatchLessonTimelineView.as_view(), name='batch-timeline'),
    path('batches/<int:batch_id>/monthly-attendance/', BatchTrainingLogView.as_view(), name='monthly-attendance'),
    path('batches/<int:batch_id>/training-log/', BatchTrainingLogView.as_view(), name='training-log'),
    path('batches/<int:batch_id>/zone-report/', BatchZoneReportView.as_view(), name='zone-report'),
    path('batches/<int:batch_id>/full-zone-report/', BatchFullZoneReportView.as_view(), name='full-zone-report'),
    path('batches/<int:batch_id>/students/<int:student_id>/profile/', StudentProfileView.as_view(), name='student-profile'),
    path('mock-eligibility/', MockEligibilityView.as_view(), name='mock-eligibility'),
    path('mock-schedule-individual/', ScheduleIndividualInterviewView.as_view(), name='mock-schedule-individual'),
    path('mock-invite/', SendMockInviteView.as_view(), name='mock-invite'),
    path('absent-students/', AbsentStudentsView.as_view(), name='absent-students'),
    path('notify-absent-students/', NotifyAbsentStudentsView.as_view(), name='notify-absent-students'),
    path('recordings/', ClassRecordingListCreateView.as_view(), name='recordings'),
    path('recordings/<int:recording_id>/share/', ShareRecordingView.as_view(), name='recording-share'),
    path('recordings/track/<str:token>/', RecordingClickTrackView.as_view(), name='recording-track'),
    path('recordings/<int:recording_id>/stats/', RecordingStatsView.as_view(), name='recording-stats'),
    path('batches/<int:batch_id>/enrollment-status/', BatchEnrollmentStatusView.as_view(), name='batch-enrollment-status'),
    path('mark-discontinued/', MarkDiscontinuedView.as_view(), name='mark-discontinued'),
    path('reactivate-student/', ReactivateStudentView.as_view(), name='reactivate-student'),
    path('email-zone-report/', EmailZoneReportView.as_view(), name='email-zone-report'),
    
] + router.urls