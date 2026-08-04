from django.core.management.base import BaseCommand
from django.utils import timezone
from core.email_utils import send_email
from admissions.models import Installment


class Command(BaseCommand):
    help = "Sends a reminder email to students whose next EMI installment is due soon."

    def handle(self, *args, **options):
        today = timezone.now().date()
        reminder_window_days = 3  # remind 3 days before due date

        target_date = today + timezone.timedelta(days=reminder_window_days)

        upcoming = Installment.objects.filter(
            paid=False,
            reminder_sent=False,
            due_date=target_date,
        ).select_related('payment__enquiry')

        if not upcoming.exists():
            self.stdout.write("No installments due for a reminder today.")
            return

        sent_count = 0
        for installment in upcoming:
            enquiry = installment.payment.enquiry
            if not enquiry.personal_email:
                self.stdout.write(self.style.WARNING(
                    f"Skipping {enquiry.name} — no personal email on file."
                ))
                continue

            sent = send_email(
                to=enquiry.personal_email,
                subject=f"Payment Reminder — Installment {installment.installment_number} Due Soon",
                html_body=(
                    f"<p>Hi {enquiry.name},</p>"
                    f"<p>This is a reminder that your installment "
                    f"<strong>#{installment.installment_number}</strong> of "
                    f"<strong>₹{installment.amount}</strong> for the "
                    f"<strong>{enquiry.course.name}</strong> course is due on "
                    f"<strong>{installment.due_date}</strong>.</p>"
                    f"<p>Please make the payment on time to avoid any delay in your enrollment.</p>"
                    f"<p>If you've already paid, please ignore this message.</p>"
                ),
            )
            if sent:
                installment.reminder_sent = True
                installment.save(update_fields=['reminder_sent'])
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f"Reminder sent to {enquiry.name} ({enquiry.personal_email})"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to send to {enquiry.name}"))

        self.stdout.write(self.style.SUCCESS(f"Done. {sent_count} reminder(s) sent."))