from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
import re


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    tenth_marksheet_url = serializers.SerializerMethodField()
    twelfth_marksheet_url = serializers.SerializerMethodField()
    degree_certificate_url = serializers.SerializerMethodField()
    pg_certificate_url = serializers.SerializerMethodField()
    terms_conditions_doc_url = serializers.SerializerMethodField()
    experience_certificate_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'phone', 'first_name', 'last_name', 'bio',
            'profile_photo', 'submission_email', 'submission_imap_host',
            'personal_email', 'official_email',
            'tenth_school', 'tenth_year', 'tenth_percentage',
            'twelfth_school', 'twelfth_year', 'twelfth_percentage',
            'ug_degree', 'ug_college', 'ug_year', 'ug_percentage',
            'pg_degree', 'pg_college', 'pg_year', 'pg_percentage',
            'tenth_marksheet_url', 'twelfth_marksheet_url', 'degree_certificate_url',
            'pg_certificate_url', 'terms_conditions_doc_url', 'experience_certificate_url',
        ]

    def get_tenth_marksheet_url(self, obj):
        return obj.tenth_marksheet.url if obj.tenth_marksheet else None

    def get_twelfth_marksheet_url(self, obj):
        return obj.twelfth_marksheet.url if obj.twelfth_marksheet else None

    def get_degree_certificate_url(self, obj):
        return obj.degree_certificate.url if obj.degree_certificate else None

    def get_pg_certificate_url(self, obj):
        return obj.pg_certificate.url if obj.pg_certificate else None

    def get_terms_conditions_doc_url(self, obj):
        return obj.terms_conditions_doc.url if obj.terms_conditions_doc else None

    def get_experience_certificate_url(self, obj):
        return obj.experience_certificate.url if obj.experience_certificate else None
class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'bio',
            'submission_email', 'submission_email_password', 'submission_imap_host',
            'personal_email',
            'tenth_school', 'tenth_year', 'tenth_percentage',
            'twelfth_school', 'twelfth_year', 'twelfth_percentage',
            'ug_degree', 'ug_college', 'ug_year', 'ug_percentage',
            'pg_degree', 'pg_college', 'pg_year', 'pg_percentage',
        ]
        # official_email deliberately excluded — students cannot self-report it,
        # it's set by office staff via Django admin once fees are confirmed.


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'phone']
        read_only_fields = ['id']

    def validate_username(self, value):
        if not re.match(r'^[A-Za-z0-9]+$', value):
            raise serializers.ValidationError("Username must be alphanumeric only (no spaces or symbols).")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_password(self, value):
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one number.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', 'student'),
            phone=validated_data.get('phone', ''),
        )
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

class CreateTrainerSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    personal_email = serializers.EmailField()
    official_email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("That username is already taken.")
        return value   

class UpdateOfficialEmailSerializer(serializers.Serializer):
    official_email = serializers.EmailField()     