from rest_framework import serializers
from .models import Course, Enquiry
from .models import Payment, Installment
from decimal import Decimal
from .models import WelcomeKit


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'max_age', 'is_active']


class EnquirySerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_max_age = serializers.IntegerField(source='course.max_age', read_only=True)
    age = serializers.ReadOnlyField()
    eligible = serializers.ReadOnlyField()
    account_created = serializers.BooleanField(source='account_created_id', read_only=True)

    class Meta:
        model = Enquiry
        fields = [
            'id', 'name', 'date_of_birth', 'whatsapp_number', 'personal_email', 'address',
            'course', 'course_name', 'course_max_age', 'education_summary', 'source',
            'status', 'notes', 'created_at', 'age', 'eligible', 'account_created',
        ]
class EnquiryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ['name', 'date_of_birth', 'whatsapp_number', 'personal_email', 'course', 'education_summary', 'source', 'address']


class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = ['id', 'installment_number', 'amount', 'due_date', 'paid', 'paid_on', 'reminder_sent']


class PaymentSerializer(serializers.ModelSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)
    total_payable = serializers.ReadOnlyField()
    fully_paid = serializers.ReadOnlyField()
    first_installment_paid = serializers.ReadOnlyField()
    enquiry_name = serializers.CharField(source='enquiry.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'enquiry', 'enquiry_name', 'base_fee', 'gst_percentage', 'plan_type',
            'installment_count', 'total_payable', 'fully_paid', 'first_installment_paid',
            'installments', 'created_at',
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['enquiry', 'base_fee', 'gst_percentage', 'plan_type', 'installment_count']

    def create(self, validated_data):
        payment = Payment.objects.create(**validated_data)

        total = payment.total_payable
        count = payment.installment_count if payment.plan_type == 'emi' else 1
        per_installment = (total / Decimal(count)).quantize(Decimal('0.01'))

        from datetime import date, timedelta
        today = date.today()
        remaining = total
        for i in range(1, count + 1):
            amt = per_installment if i < count else (remaining - per_installment * (count - 1))
            Installment.objects.create(
                payment=payment,
                installment_number=i,
                amount=amt,
                due_date=today + timedelta(days=30 * (i - 1)),
            )
        return payment      


from django.contrib.auth import get_user_model
User = get_user_model()


class CreateAccountSerializer(serializers.Serializer):
    enquiry_id = serializers.IntegerField()
    username = serializers.CharField()
    password = serializers.CharField()
    official_email = serializers.EmailField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("That username is already taken.")
        return value      


class GroupIntoBatchSerializer(serializers.Serializer):
    enquiry_ids = serializers.ListField(child=serializers.IntegerField())
    batch_name = serializers.CharField()
    trainer_id = serializers.IntegerField()
    course_name = serializers.CharField()
    training_mode = serializers.CharField(default='Online')
    programming_language = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    class_start_time = serializers.TimeField(required=False, allow_null=True)
    max_students = serializers.IntegerField(default=45)    


class WelcomeKitSerializer(serializers.ModelSerializer):
    enquiry_name = serializers.CharField(source='enquiry.name', read_only=True)
    address = serializers.CharField(source='enquiry.address', read_only=True)

    class Meta:
        model = WelcomeKit
        fields = [
            'id', 'enquiry', 'enquiry_name', 'address', 'sent', 'sent_date',
            'courier_name', 'tracking_id', 'received', 'received_date', 'notes', 'updated_at',
        ]    


class PaymentListSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    payment_id = serializers.IntegerField(source='payment.id', read_only=True)
    base_fee = serializers.DecimalField(source='payment.base_fee', max_digits=10, decimal_places=2, read_only=True)
    gst_percentage = serializers.DecimalField(source='payment.gst_percentage', max_digits=5, decimal_places=2, read_only=True)
    plan_type = serializers.CharField(source='payment.plan_type', read_only=True)
    installment_count = serializers.IntegerField(source='payment.installment_count', read_only=True)
    total_payable = serializers.SerializerMethodField()
    fully_paid = serializers.SerializerMethodField()
    first_installment_paid = serializers.SerializerMethodField()
    next_due_installment = serializers.SerializerMethodField()
    due_soon = serializers.SerializerMethodField()
    age = serializers.ReadOnlyField()
    eligible = serializers.ReadOnlyField()

    class Meta:
        model = Enquiry
        fields = [
            'id', 'name', 'whatsapp_number', 'personal_email', 'course_name', 'payment_id',
            'base_fee', 'gst_percentage', 'total_payable', 'plan_type', 'installment_count',
            'fully_paid', 'first_installment_paid', 'next_due_installment', 'due_soon',
            'age', 'eligible',
        ]

    def get_total_payable(self, obj):
        return obj.payment.total_payable

    def get_fully_paid(self, obj):
        return obj.payment.fully_paid

    def get_first_installment_paid(self, obj):
        return obj.payment.first_installment_paid

    def get_next_due_installment(self, obj):
        inst = obj.payment.installments.filter(paid=False).order_by('installment_number').first()
        if not inst:
            return None
        return {'installment_number': inst.installment_number, 'amount': str(inst.amount), 'due_date': inst.due_date}

    def get_due_soon(self, obj):
        from datetime import date
        inst = obj.payment.installments.filter(paid=False).order_by('installment_number').first()
        if not inst:
            return False
        days_left = (inst.due_date - date.today()).days
        return 0 <= days_left <= 3