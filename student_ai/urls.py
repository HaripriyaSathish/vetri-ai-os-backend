from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.StudentDashboardView.as_view(), name="student-dashboard"),
    path("attendance/", views.StudentAttendanceListView.as_view(), name="student-attendance"),
    path("assignments/", views.StudentAssignmentListView.as_view(), name="student-assignments"),
    path(
        "assignments/submit/",
        views.StudentAssignmentSubmitView.as_view(),
        name="student-assignment-submit",
    ),
    path("assessments/", views.StudentAssessmentListView.as_view(), name="student-assessments"),
    path("eligibility/", views.StudentEligibilityView.as_view(), name="student-eligibility"),
    path("progress/", views.StudentProgressView.as_view(), name="student-progress"),
    path("messages/", views.StudentMessageListCreateView.as_view(), name="student-messages"),
    path("messages/mark-read/", views.MarkMessagesReadView.as_view(), name="student-messages-mark-read"),
    path("notifications/", views.StudentNotificationListView.as_view(), name="student-notifications"),
    path(
        "notifications/<int:pk>/read/",
        views.MarkNotificationReadView.as_view(),
        name="student-notification-read",
    ),
    path(
        "notifications/read-all/",
        views.MarkAllNotificationsReadView.as_view(),
        name="student-notifications-read-all",
    ),
    path("recordings/", views.StudentRecordingListView.as_view(), name="student-recordings"),
    path("reports/<str:period>/download/", views.StudentZoneReportDownloadView.as_view(), name="student-report-download"),
]
