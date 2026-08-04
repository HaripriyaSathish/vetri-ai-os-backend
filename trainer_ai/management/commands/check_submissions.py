import imaplib
import email
import re
from email.header import decode_header
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from trainer_ai.models import Assignment, AssignmentSubmission

User = get_user_model()

# Common filler words to ignore when comparing subject to assignment titles
STOPWORDS = {
    'submission', 'of', 'for', 'the', 'a', 'an', 'assignment', 'task',
    'project', 'submit', 'submitting', 're', 'fwd',
}


def normalize_words(text):
    """Lowercase, strip punctuation, split into meaningful words."""
    text = re.sub(r'[^a-z0-9\s]', ' ', text.lower())
    words = [w for w in text.split() if w and w not in STOPWORDS]
    return set(words)


class Command(BaseCommand):
    help = "Checks every trainer's submission inbox for new assignment emails and logs them."

    def handle(self, *args, **options):
        trainers = User.objects.filter(
            role='trainer',
            submission_email__isnull=False,
            submission_email_password__isnull=False,
        ).exclude(submission_email='')

        if not trainers.exists():
            self.stdout.write("No trainers have configured a submission inbox yet.")
            return

        for trainer in trainers:
            self.stdout.write(f"Checking inbox for {trainer.username} ({trainer.submission_email})...")
            self.check_inbox(trainer)

        self.stdout.write(self.style.SUCCESS("Done checking all trainer inboxes."))

    def find_best_assignment_match(self, subject, trainer):
        subject_words = normalize_words(subject)
        if not subject_words:
            return None

        assignments = Assignment.objects.filter(batch__trainer=trainer)
        best_match = None
        best_score = 0

        for assignment in assignments:
            title_words = normalize_words(assignment.title)
            if not title_words:
                continue
            overlap = subject_words & title_words
            score = len(overlap)
            if score > best_score:
                best_score = score
                best_match = assignment

        # Require at least 1 real matching word to avoid false positives
        if best_score >= 1:
            return best_match
        return None

    def check_inbox(self, trainer):
        try:
            host = trainer.submission_imap_host or 'imap.hostinger.com'
            mail = imaplib.IMAP4_SSL(host)
            mail.login(trainer.submission_email, trainer.submission_email_password)
            mail.select('inbox')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect for {trainer.username}: {e}"))
            return

        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        self.stdout.write(f"  Found {len(email_ids)} unread email(s).")

        for eid in email_ids:
            status, msg_data = mail.fetch(eid, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            sender = email.utils.parseaddr(msg.get('From'))[1]
            subject = decode_header(msg.get('Subject'))[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors='ignore')

            received_date = email.utils.parsedate_to_datetime(msg.get('Date')).date()
            submitted_datetime = timezone.make_aware(datetime.combine(received_date, datetime.min.time()))

            # Loosely check this looks like a submission email at all
            if 'submi' not in subject.lower():  # catches "submit", "submission", "submitting"
                self.stdout.write(f"  Skipping '{subject}' — doesn't look like a submission email.")
                continue

            try:
                student = User.objects.get(email__iexact=sender, role='student')
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  No registered student found for {sender}. Skipping."))
                continue

            assignment = self.find_best_assignment_match(subject, trainer)
            if not assignment:
                self.stdout.write(self.style.WARNING(f"  No assignment matched subject '{subject}'. Skipping."))
                continue

            submission, created = AssignmentSubmission.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    'submitted_at': submitted_datetime,
                    'remarks': f"Auto-logged from email received {received_date} (subject: \"{subject}\")",
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"  Logged: {student.username} -> {assignment.title} ({received_date})"
                ))
            else:
                self.stdout.write(f"  Already logged: {student.username} -> {assignment.title}")

        mail.logout()