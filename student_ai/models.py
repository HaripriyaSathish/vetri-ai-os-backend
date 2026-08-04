from django.conf import settings
from django.db import models


class StudentNotification(models.Model):
    """
    In-app notification bell feed for a student. Populated by signals.py:
      - a new Assignment posted to their batch
      - a new Message from their trainer (trainer_ai.Message, sender side)
      - a new batch Report generated that mentions them

    NOTE: leave requests / doubt clarification do NOT get a new model here.
    They reuse trainer_ai's existing `Message` model (sender/recipient
    already restricts a thread to exactly two people — a student can only
    ever see messages where they are the sender or recipient, so batchmates
    are excluded automatically). See TRAINER_AI_PATCHES.md for the small,
    additive `category` field patch that lets a message be tagged
    Leave Request / Doubt / General.
    """

    TYPE_CHOICES = [
        ("assignment", "New Assignment"),
        ("reminder", "Assignment Reminder"),
        ("message", "New Message From Trainer"),
        ("report", "Progress Report Ready"),
        ("general", "General"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_notifications",
    )
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="general")
    title = models.CharField(max_length=200)
    message = models.CharField(max_length=500, blank=True)
    related_link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notif_type} -> {self.student}: {self.title}"
