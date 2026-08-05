from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Course, Enquiry
from .serializers import CourseSerializer, EnquirySerializer, EnquiryCreateSerializer
from .models import Payment, Installment
from .serializers import PaymentSerializer, PaymentCreateSerializer
from io import BytesIO
import os
from django.http import FileResponse
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from .utils import amount_in_words
from .serializers import PaymentListSerializer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from decimal import Decimal


class CourseListView(generics.ListAPIView):
    """Public — populates the course dropdown on the enquiry form."""
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Course.objects.filter(is_active=True)


class EnquiryCreateView(generics.CreateAPIView):
    """Public — the enquiry form submits here. No login needed."""
    serializer_class = EnquiryCreateSerializer
    permission_classes = [permissions.AllowAny]


class EnquiryListView(generics.ListAPIView):
    """Business team only — full list, with age/eligibility already computed."""
    serializer_class = EnquirySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role not in ('admin', 'management'):
            return Enquiry.objects.none()
        qs = Enquiry.objects.all()
        status_filter = self.request.query_params.get('status')
        eligible_only = self.request.query_params.get('eligible_only')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if eligible_only == 'true':
            ids = [e.id for e in qs if e.eligible]
            qs = qs.filter(id__in=ids)
        return qs


class EnquiryUpdateStatusView(APIView):
    """Business team only — shortlist / reject / add notes."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)
        try:
            enquiry = Enquiry.objects.get(id=pk)
        except Enquiry.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        new_status = request.data.get('status')
        if new_status:
            enquiry.status = new_status
        if 'notes' in request.data:
            enquiry.notes = request.data['notes']
        enquiry.save()
        return Response(EnquirySerializer(enquiry).data)


class CourseViewSet(generics.ListCreateAPIView):
    """Business team manages courses and their age limits here."""
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Course.objects.all()


class CourseDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Course.objects.all()

class PaymentCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentCreateSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)
        return super().create(request, *args, **kwargs)


class PaymentDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()
    lookup_field = 'enquiry_id'
    lookup_url_kwarg = 'enquiry_id'


class MarkInstallmentPaidView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)
        try:
            installment = Installment.objects.get(id=pk)
        except Installment.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        from datetime import date
        installment.paid = True
        installment.paid_on = date.today()
        installment.save()
        return Response(PaymentSerializer(installment.payment).data)    


from django.contrib.auth import get_user_model
from .serializers import CreateAccountSerializer
from .models import Payment

User = get_user_model()


class SuggestUsernameView(APIView):
    """Suggests a free username based on the enquiry's name."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, enquiry_id):
        try:
            enquiry = Enquiry.objects.get(id=enquiry_id)
        except Enquiry.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        base = ''.join(ch for ch in enquiry.name.lower() if ch.isalnum())[:15] or 'student'
        candidate = base
        counter = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}{counter}"
            counter += 1

        official_email = f"{candidate}@vetrifresh.com"  # ADAPT: change domain if needed
        return Response({"suggested_username": candidate, "suggested_official_email": official_email})


class CreateAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        serializer = CreateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            enquiry = Enquiry.objects.get(id=data['enquiry_id'])
        except Enquiry.DoesNotExist:
            return Response({"detail": "Enquiry not found."}, status=404)

        if enquiry.account_created_id:
            return Response({"detail": "An account already exists for this enquiry."}, status=400)

        try:
            payment = enquiry.payment
        except Payment.DoesNotExist:
            return Response({"detail": "No payment plan set up for this enquiry yet."}, status=400)

        if not (payment.fully_paid or payment.first_installment_paid):
            return Response({"detail": "Payment not yet verified — need full payment or first installment paid."}, status=400)

        name_parts = enquiry.name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        student = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            role='student',
            first_name=first_name,
            last_name=last_name,
            personal_email=enquiry.personal_email,
            official_email=data['official_email'],
            phone=enquiry.whatsapp_number,
        )

        enquiry.account_created = student
        enquiry.created_password = data['password']
        enquiry.save(update_fields=['account_created', 'created_password'])

        return Response({
            "detail": "Account created successfully.",
            "username": student.username,
            "official_email": student.official_email,
        }, status=201)    


from django.contrib.auth import get_user_model
from trainer_ai.models import Batch, Attendance
from django.utils import timezone
from core.email_utils import send_email
from .serializers import GroupIntoBatchSerializer

User = get_user_model()


class UngroupedStudentsView(APIView):
    """Students who've paid and have an account, but aren't in a batch yet."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        enquiries = Enquiry.objects.filter(
            account_created__isnull=False,
        ).exclude(status='converted')

        return Response(EnquirySerializer(enquiries, many=True).data)


class GroupIntoBatchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        serializer = GroupIntoBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            trainer = User.objects.get(id=data['trainer_id'], role='trainer')
        except User.DoesNotExist:
            return Response({"detail": "Trainer not found."}, status=404)

        enquiries = Enquiry.objects.filter(id__in=data['enquiry_ids'], account_created__isnull=False)
        if not enquiries.exists():
            return Response({"detail": "No valid students selected."}, status=400)

        batch = Batch.objects.create(
            name=data['batch_name'],
            trainer=trainer,
            start_date=data['start_date'],
            end_date=data.get('end_date'),
            course_name=data['course_name'],
            training_mode=data.get('training_mode', 'Online'),
            programming_language=data.get('programming_language', ''),
            class_start_time=data.get('class_start_time'),
            class_end_time=data.get('class_end_time'),
            max_students=data.get('max_students', 45),
        )

        roster = []
        for enquiry in enquiries:
            student = enquiry.account_created
            Attendance.objects.create(
                batch=batch,
                student=student,
                date=timezone.now().date(),
                status='present',
                marked_by=request.user,
            )
            enquiry.status = 'converted'
            enquiry.save(update_fields=['status'])
            roster.append(student)

        # No more auto-sending here — frontend now shows an editable
        # email modal for both the trainer notification and student welcome emails.

        return Response({
            "detail": f"Batch created with {len(roster)} student(s).",
            "batch_id": batch.id,
            "trainer": {
                "id": trainer.id,
                "name": f"{trainer.first_name} {trainer.last_name}".strip() or trainer.username,
                "email": trainer.official_email or trainer.email or '',
            },
            "roster": [
                {
                    "id": s.id,
                    "name": f"{s.first_name} {s.last_name}".strip() or s.username,
                    "personal_email": s.personal_email,
                    "official_email": s.official_email,
                }
                for s in roster
            ],
        }, status=201)


from .models import WelcomeKit
from .serializers import WelcomeKitSerializer


class WelcomeKitDetailView(APIView):
    """Get or create-on-demand the welcome kit record for an enquiry."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, enquiry_id):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)
        try:
            enquiry = Enquiry.objects.get(id=enquiry_id)
        except Enquiry.DoesNotExist:
            return Response({"detail": "Enquiry not found."}, status=404)

        kit, _ = WelcomeKit.objects.get_or_create(enquiry=enquiry)
        return Response(WelcomeKitSerializer(kit).data)


class WelcomeKitUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)
        try:
            kit = WelcomeKit.objects.get(id=pk)
        except WelcomeKit.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        from datetime import date
        data = request.data

        if 'sent' in data:
            kit.sent = data['sent']
            if kit.sent and not kit.sent_date:
                kit.sent_date = date.today()
        if 'courier_name' in data:
            kit.courier_name = data['courier_name']
        if 'tracking_id' in data:
            kit.tracking_id = data['tracking_id']
        if 'received' in data:
            kit.received = data['received']
            if kit.received and not kit.received_date:
                kit.received_date = date.today()
        if 'notes' in data:
            kit.notes = data['notes']

        kit.save()
        return Response(WelcomeKitSerializer(kit).data)    




class PaymentsListView(generics.ListAPIView):
    serializer_class = PaymentListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role not in ('admin', 'management'):
            return Enquiry.objects.none()
        return Enquiry.objects.filter(payment__isnull=False).select_related('payment', 'course')


class InvoiceDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, enquiry_id):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        try:
            enquiry = Enquiry.objects.get(id=enquiry_id)
            payment = enquiry.payment
        except (Enquiry.DoesNotExist, Payment.DoesNotExist):
            return Response({"detail": "Enquiry or payment plan not found."}, status=404)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
        styles = getSampleStyleSheet()
        elements = []

        blue = colors.HexColor('#0051D5')
        black = colors.black
        grey_bg = colors.HexColor('#F1F5F9')

        title_style = ParagraphStyle('TitleBlue', parent=styles['Title'], textColor=blue, alignment=TA_CENTER, fontSize=18, spaceAfter=2)
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11, textColor=blue, spaceAfter=2)
        contact_style = ParagraphStyle('Contact', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=blue, spaceAfter=6)
        billing_date_style = ParagraphStyle('BillingDate', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=10, textColor=black, fontName='Helvetica-Bold')

        header_content = []
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'vetri-logo.jpg')
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=22 * mm, height=22 * mm)
            logo.hAlign = 'CENTER'
            header_content.append(logo)
            header_content.append(Spacer(1, 3 * mm))
        header_content.append(Paragraph('Vetri Technology Solutions', title_style))
        header_content.append(Paragraph('IT Training with 100% Placement', subtitle_style))
        header_content.append(Paragraph('Contact Us: 8438558527, 8438558627', contact_style))
        billing_date = timezone.now().strftime('%d-%m-%Y')
        header_content.append(Paragraph(f"Billing Date: {billing_date}", billing_date_style))

        header_table = Table([[header_content]], colWidths=[155 * mm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), grey_bg),
            ('BOX', (0, 0), (-1, -1), 1, blue),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10 * mm))

        label_style = ParagraphStyle('Label', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=black, fontSize=10)
        value_style = ParagraphStyle('Value', parent=styles['Normal'], textColor=blue, fontSize=10)

        gst_amount = payment.total_payable - payment.base_fee
        installments = payment.installments.all().order_by('installment_number')
        paid_amount = sum((i.amount for i in installments if i.paid), start=Decimal('0'))
        balance_amount = payment.total_payable - paid_amount
        next_installment = installments.filter(paid=False).order_by('installment_number').first()

        rows = [
            ('Bill No:', str(payment.id)),
            ('Trainee Name:', enquiry.name),
            ('Certification Name:', enquiry.course.name),
            ('Date of Joining:', enquiry.created_at.strftime('%b. %d, %Y')),
            ('Base Fee:', f"Rs.{payment.base_fee}"),
            (f"GST ({payment.gst_percentage}%):", f"Rs.{gst_amount:.2f}"),
            ('Total Amount:', f"Rs.{payment.total_payable:.2f}"),
            ('Amount Paid:', f"Rs.{paid_amount:.2f}"),
            ('Balance Amount:', f"Rs.{balance_amount:.2f}"),
        ]
        if next_installment:
            rows.append((
                f"Next Installment (#{next_installment.installment_number}):",
                f"Rs.{next_installment.amount} due {next_installment.due_date.strftime('%d-%m-%Y')}",
            ))
        rows.append(('Amount in Words:', amount_in_words(payment.total_payable)))

        data = [[Paragraph(label, label_style), Paragraph(value, value_style)] for label, value in rows]

        table = Table(data, colWidths=[55 * mm, 100 * mm])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.75, blue),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20 * mm))

        sig_style_left = ParagraphStyle('SigLeft', parent=styles['Normal'], textColor=blue, fontSize=10)
        sig_style_right = ParagraphStyle('SigRight', parent=styles['Normal'], textColor=blue, fontSize=10, alignment=2)
        sig_table = Table([[Paragraph('Trainee Signature', sig_style_left), Paragraph('Admin Signature', sig_style_right)]], colWidths=[77 * mm, 77 * mm])
        elements.append(sig_table)

        doc.build(elements)
        buffer.seek(0)
        filename = f"{enquiry.name.replace(' ', '_')}_Invoice.pdf"
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')


class EnquiriesWithoutPaymentView(generics.ListAPIView):
    serializer_class = EnquirySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role not in ('admin', 'management'):
            return Enquiry.objects.none()
        return Enquiry.objects.filter(payment__isnull=True).exclude(status='rejected')    

class NewEnquiryCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('admin', 'management'):
            return Response({"new_count": 0})
        count = Enquiry.objects.filter(status='new', seen=False).count()
        return Response({"new_count": count})


class MarkEnquiriesSeenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)
        Enquiry.objects.filter(status='new', seen=False).update(seen=True)
        return Response({"detail": "Marked as seen."})


class DeletePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, payment_id):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment plan not found."}, status=404)
        payment.delete()
        return Response({"detail": "Payment plan deleted."}, status=204)        