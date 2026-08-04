from django.db import models
from datetime import date
from django.conf import settings


class Course(models.Model):
    """A course offering — e.g. 'AI Fullstack', 'Digital Marketing'.
    Each has its own age eligibility limit, editable anytime."""
    name = models.CharField(max_length=100, unique=True)
    max_age = models.PositiveIntegerField(help_text="Maximum eligible age for this course")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (max age {self.max_age})"


class Enquiry(models.Model):
    SOURCE_CHOICES = [
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('referral', 'Referral'),
        ('walk_in', 'Walk-in'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('new', 'New'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted'),  # became a paying student
    ]

    name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    whatsapp_number = models.CharField(max_length=20)
    personal_email = models.EmailField(blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enquiries')
    education_summary = models.CharField(max_length=300, blank=True, null=True, help_text="e.g. B.E. CSE, 2024 pass-out")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)
    account_created = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='enquiry_source'
    )
    address = models.TextField(blank=True, null=True, help_text="Shipping address for welcome kit")
    class Meta:
        ordering = ['-created_at']

    @property
    def age(self):
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def eligible(self):
        return self.age <= self.course.max_age

    def __str__(self):
        return f"{self.name} - {self.course.name} ({self.status})"


from decimal import Decimal, ROUND_HALF_UP


class Payment(models.Model):
    PLAN_CHOICES = [
        ('full', 'Full Payment'),
        ('emi', 'EMI'),
    ]

    enquiry = models.OneToOneField(Enquiry, on_delete=models.CASCADE, related_name='payment')
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Course fee before GST")
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    plan_type = models.CharField(max_length=10, choices=PLAN_CHOICES, default='full')
    installment_count = models.PositiveIntegerField(default=1, help_text="1 for full payment, 2+ for EMI")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_payable(self):
        gst_amount = (self.base_fee * self.gst_percentage / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return self.base_fee + gst_amount

    @property
    def fully_paid(self):
        return all(inst.paid for inst in self.installments.all())

    @property
    def first_installment_paid(self):
        first = self.installments.order_by('installment_number').first()
        return first.paid if first else False

    def __str__(self):
        return f"{self.enquiry.name} - {self.plan_type} ({self.installment_count})"


class Installment(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='installments')
    installment_number = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid = models.BooleanField(default=False)
    paid_on = models.DateField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['installment_number']
        unique_together = ['payment', 'installment_number']

    def __str__(self):
        return f"Installment {self.installment_number} - {self.payment.enquiry.name} ({'Paid' if self.paid else 'Due'})"

class WelcomeKit(models.Model):
    enquiry = models.OneToOneField(Enquiry, on_delete=models.CASCADE, related_name='welcome_kit')
    sent = models.BooleanField(default=False)
    sent_date = models.DateField(null=True, blank=True)
    courier_name = models.CharField(max_length=100, blank=True, null=True)
    tracking_id = models.CharField(max_length=100, blank=True, null=True)
    received = models.BooleanField(default=False)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Welcome Kit - {self.enquiry.name}"    