from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Vetri AI-OS Profile', {
            'fields': ('role', 'phone', 'bio', 'profile_photo')
        }),
        ('Assignment Submission Inbox', {
            'fields': ('submission_email', 'submission_email_password', 'submission_imap_host')
        }),
        ('Contact — Personal & Official', {
            'fields': ('personal_email', 'official_email'),
            'description': 'Official email is assigned by office staff once fees are confirmed.',
        }),
        ('Education — 10th & 12th', {
            'fields': (
                'tenth_school', 'tenth_year', 'tenth_percentage', 'tenth_marksheet',
                'twelfth_school', 'twelfth_year', 'twelfth_percentage', 'twelfth_marksheet',
            )
        }),
        ('Education — UG & PG', {
            'fields': (
                'ug_degree', 'ug_college', 'ug_year', 'ug_percentage', 'degree_certificate',
                'pg_degree', 'pg_college', 'pg_year', 'pg_percentage',
            )
        }),
    )
    list_display = ('username', 'email', 'role', 'official_email', 'submission_email')


admin.site.register(User, CustomUserAdmin)