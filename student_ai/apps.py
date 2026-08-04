from django.apps import AppConfig


class StudentAiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "student_ai"
    verbose_name = "Student AI"

    def ready(self):
        from . import signals  # noqa: F401
