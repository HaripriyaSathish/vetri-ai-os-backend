from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField


class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    MANAGEMENT = 'management', 'Management'
    TRAINER = 'trainer', 'Trainer'
    STUDENT = 'student', 'Student'
    INTERN = 'intern', 'Intern'
    HR = 'hr', 'HR'


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.URLField(blank=True, null=True)
    bio = models.CharField(max_length=300, blank=True, null=True)
    submission_email = models.EmailField(blank=True, null=True)
    submission_email_password = models.CharField(max_length=255, blank=True, null=True)
    submission_imap_host = models.CharField(max_length=100, blank=True, null=True, default='imap.hostinger.com')
    created_at = models.DateTimeField(auto_now_add=True)

    # NEW — student personal & official contact info
    personal_email = models.EmailField(blank=True, null=True, help_text="Student's own email, separate from login email")
    official_email = models.EmailField(blank=True, null=True, help_text="Assigned by office once fees are paid")

    # NEW — education history
    tenth_school = models.CharField(max_length=200, blank=True, null=True)
    tenth_year = models.PositiveIntegerField(blank=True, null=True)
    tenth_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    twelfth_school = models.CharField(max_length=200, blank=True, null=True)
    twelfth_year = models.PositiveIntegerField(blank=True, null=True)
    twelfth_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    ug_degree = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. B.E. Computer Science")
    ug_college = models.CharField(max_length=200, blank=True, null=True)
    ug_year = models.PositiveIntegerField(blank=True, null=True)
    ug_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    pg_degree = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. M.E. Software Engineering — leave blank if not applicable")
    pg_college = models.CharField(max_length=200, blank=True, null=True)
    pg_year = models.PositiveIntegerField(blank=True, null=True)
    pg_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    # NEW — certificate uploads (PDF), stored on Cloudinary
    tenth_marksheet = CloudinaryField('raw', resource_type='raw', folder='vetri_ai_os/certificates', blank=True, null=True)
    twelfth_marksheet = CloudinaryField('raw', resource_type='raw', folder='vetri_ai_os/certificates', blank=True, null=True)
    degree_certificate = CloudinaryField('raw', resource_type='raw', folder='vetri_ai_os/certificates', blank=True, null=True)
    terms_conditions_doc = CloudinaryField('raw', resource_type='raw', folder='vetri_ai_os/certificates', blank=True, null=True, help_text="Signed Terms & Conditions (student)")
    trainer_certificate = CloudinaryField('raw', resource_type='raw', folder='vetri_ai_os/certificates', blank=True, null=True, help_text="Trainer's certificate/resume")
    pg_certificate = CloudinaryField('raw', resource_type='raw', folder='vetri_ai_os/certificates', blank=True, null=True, help_text="PG degree certificate")
    experience_certificate = CloudinaryField('raw', resource_type='raw', folder='vetri_ai_os/certificates', blank=True, null=True, help_text="Trainer's work experience certificate")
    def save(self, *args, **kwargs):
        # Once an official email is assigned (e.g. by office staff after fee
        # confirmation), it becomes the account's login email too — so both
        # fields always match from that point forward.
        if self.official_email:
            self.email = self.official_email
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"