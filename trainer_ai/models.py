from django.conf import settings
from django.db import models
from cloudinary.models import CloudinaryField


class Batch(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
    ]

    name = models.CharField(max_length=100)
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='batches')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ongoing')
    planned_topics = models.TextField(blank=True, null=True)
    max_students = models.PositiveIntegerField(default=45)
    programming_language = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. Java, Python")
    training_mode = models.CharField(max_length=20, default='Online')
    course_name = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. AI FULLSTACK")
    created_at = models.DateTimeField(auto_now_add=True)
    class_start_time = models.TimeField(null=True, blank=True, help_text="Daily class start time")
    def __str__(self):
        return self.name


class LessonPlan(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='lesson_plans')
    topic = models.CharField(max_length=200)
    content = models.TextField()  # AI-generated or manually written
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} ({self.batch.name})"

class DailySchedule(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    topic = models.CharField(max_length=200)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.batch.name} - {self.date} ({self.topic})"    


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='attendance_marked')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['batch', 'student', 'date']

    def __str__(self):
        return f"{self.student.username} - {self.date} ({self.status})"    


class Assignment(models.Model):
    CATEGORY_CHOICES = [
        ('task', 'Daily Task'),
        ('mini_project', 'Mini Project'),
        ('main_project', 'Main Project'),
        ('seminar', 'Seminar'),
    ]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='assignments')
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='task')
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.title} ({self.batch.name})"  

class MockInterviewQuestion(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='mock_questions')
    topic = models.CharField(max_length=200)
    question = models.TextField()
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES, default='beginner')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.topic} ({self.difficulty})"     

class MockInterviewSession(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='mock_sessions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mock_sessions')
    invited_at = models.DateTimeField(auto_now_add=True)
    scheduled_datetime = models.DateTimeField(null=True, blank=True)
    meeting_link = models.URLField(max_length=1000, blank=True, null=True)  # NEW: Teams link for this student's individual slot
    attended = models.BooleanField(null=True, blank=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['batch', 'student']
        ordering = ['-invited_at']

    def __str__(self):
        return f"{self.student.username} - {self.batch.name}"

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    score = models.PositiveIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    student_note = models.TextField(blank=True, null=True)
    links = models.TextField(blank=True, null=True, help_text="GitHub/Drive links, one per line")
    cc_email = models.CharField(max_length=300, blank=True, null=True, help_text="Comma-separated CC addresses used at submission time")
    attachment = CloudinaryField('attachment', resource_type='auto', blank=True, null=True)  # kept for old records
    submitted_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title} ({self.score})"  

class SubmissionAttachment(models.Model):
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='attachments')
    file = CloudinaryField('attachment', resource_type='auto')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.submission}"    

class Report(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=200)
    content = models.TextField()  # AI-generated full report
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reports_generated')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.batch.name})"    

class Message(models.Model):
    CATEGORY_CHOICES = [
        ('leave', 'Leave Request'),
        ('doubt', 'Doubt Clarification'),
        ('general', 'General'),
    ]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='general')
    leave_from_date = models.DateField(null=True, blank=True)
    leave_to_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.content[:30]}"


class ClassRecording(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='recordings')
    date = models.DateField()
    title = models.CharField(max_length=200)
    link = models.URLField(max_length=1000, help_text="Google Drive / YouTube (unlisted) / Zoom cloud / Microsoft Teams recording link")
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='recordings_shared')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} ({self.batch.name} - {self.date})"


class RecordingView(models.Model):
    """One row per (recording, student) pair, created when the share email
    goes out. The email's link points at a tracking redirect keyed by
    `token`, so we know exactly who actually opened the recording."""
    recording = models.ForeignKey(ClassRecording, on_delete=models.CASCADE, related_name='views')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recording_views')
    token = models.CharField(max_length=64, unique=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['recording', 'student']

    def __str__(self):
        return f"{self.student.username} - {self.recording.title} ({'Watched' if self.clicked else 'Not yet'})"


class Enrollment(models.Model):
    """Tracks whether a student is still active in a batch, separate from
    day-to-day Attendance records. Lazily created (defaults to active) the
    first time a student needs a status check."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('discontinued', 'Discontinued'),
    ]
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollment_records')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    discontinued_date = models.DateField(null=True, blank=True)
    discontinued_reason = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['batch', 'student']

    def __str__(self):
        return f"{self.student.username} - {self.batch.name} ({self.status})"

class AbsenceNotification(models.Model):
    """One row per (batch, student, date) — created the moment a notify
    email actually sends, so reloading the page shows accurate history
    instead of re-offering to notify someone already notified."""
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='absence_notifications')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='absence_notifications')
    date = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['batch', 'student', 'date']

    def __str__(self):
        return f"{self.student.username} notified for absence on {self.date}"    

class Holiday(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True, default='Holiday')

    class Meta:
        unique_together = ('batch', 'date')

    def __str__(self):
        return f"{self.batch.name} — {self.date} ({self.reason})"    