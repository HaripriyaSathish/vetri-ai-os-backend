from django.contrib import admin
from .models import Course, Enquiry, Payment, Installment
from .models import WelcomeKit


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['enquiry', 'plan_type', 'installment_count', 'base_fee', 'total_payable', 'fully_paid']
    inlines = [InstallmentInline]


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ['payment', 'installment_number', 'amount', 'due_date', 'paid', 'reminder_sent']
    list_filter = ['paid', 'reminder_sent']


admin.site.register(Course)
admin.site.register(Enquiry)
admin.site.register(WelcomeKit)