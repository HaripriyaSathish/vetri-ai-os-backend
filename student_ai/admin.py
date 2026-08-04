from django.contrib import admin

from .models import StudentNotification


@admin.register(StudentNotification)
class StudentNotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "student", "notif_type", "is_read", "created_at"]
    list_filter = ["notif_type", "is_read"]
    search_fields = ["title", "message", "student__username"]
