from django.contrib import admin
from .models import (
    Batch, LessonPlan, DailySchedule, Attendance,
    Assignment, MockInterviewQuestion, AssignmentSubmission,
    Report, MockInterviewSession, Message,
)

admin.site.register(Batch)
admin.site.register(LessonPlan)
admin.site.register(DailySchedule)
admin.site.register(Attendance)
admin.site.register(Assignment)
admin.site.register(MockInterviewQuestion)
admin.site.register(AssignmentSubmission)
admin.site.register(Report)
admin.site.register(MockInterviewSession)
admin.site.register(Message)