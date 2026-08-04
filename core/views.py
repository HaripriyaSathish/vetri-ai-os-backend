from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .serializers import RegisterSerializer, UserSerializer
from django.contrib.auth import get_user_model

from decouple import config
from core.email_utils import send_email
from .serializers import ProfileUpdateSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str


User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)



class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal whether the email exists
            return Response({"detail": "If that email exists, a reset link has been sent."})

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)
        reset_link = f"{config('FRONTEND_URL')}/reset-password?uid={uid}&token={token}"

        send_email(
            to=email,
            subject="Reset your Vetri AI-OS password",
            html_body=f"<p>Hi {user.username},</p><p>Click below to reset your password:</p><p><a href='{reset_link}'>Reset Password</a></p><p>If you didn't request this, ignore this email.</p>",
        )

        return Response({"detail": "If that email exists, a reset link has been sent."})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Invalid reset link."}, status=400)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({"detail": "Reset link expired or invalid."}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password reset successful."})    


class StudentListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.filter(role='student', is_superuser=False, is_staff=False)  


import cloudinary.uploader

class UpdateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        data = request.data.copy()

        # Don't let a blank password field wipe out the real stored password
        if 'submission_email_password' in data and not data['submission_email_password']:
            data.pop('submission_email_password')

        serializer = ProfileUpdateSerializer(request.user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class UploadAvatarView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('avatar')
        if not file:
            return Response({"detail": "No file provided."}, status=400)

        upload_result = cloudinary.uploader.upload(file, folder="vetri_ai_os/avatars")
        request.user.profile_photo = upload_result['secure_url']
        request.user.save()

        return Response(UserSerializer(request.user).data)

    def delete(self, request):
        request.user.profile_photo = None
        request.user.save()
        return Response(UserSerializer(request.user).data)    

class UploadCertificateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    FIELD_MAP = {
        'tenth': 'tenth_marksheet',
        'twelfth': 'twelfth_marksheet',
        'degree': 'degree_certificate',
        'pg': 'pg_certificate',
        'terms': 'terms_conditions_doc',
        'experience': 'experience_certificate',
    }

    def post(self, request):
        cert_type = request.data.get('cert_type')
        file = request.FILES.get('file')

        if cert_type not in self.FIELD_MAP:
            return Response({"detail": "cert_type must be one of: tenth, twelfth, degree."}, status=400)
        if not file:
            return Response({"detail": "No file provided."}, status=400)
        if not file.name.lower().endswith('.pdf'):
            return Response({"detail": "Only PDF files are accepted."}, status=400)

        field_name = self.FIELD_MAP[cert_type]
        setattr(request.user, field_name, file)
        request.user.save()

        return Response(UserSerializer(request.user).data)

from django.db.models import Q


class StudentDirectoryView(APIView):
    """Full student directory for founder/business team — includes every
    registered student, even those not yet enrolled in any batch."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from trainer_ai.models import Attendance, Assignment, AssignmentSubmission, MockInterviewSession

        user = request.user
        if user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        results = []
        for student in User.objects.filter(role='student', is_superuser=False, is_staff=False).order_by('username'):
            latest_attendance = Attendance.objects.filter(student=student).order_by('-date').first()
            batch = latest_attendance.batch if latest_attendance else None

            att_qs = Attendance.objects.filter(student=student, batch=batch) if batch else Attendance.objects.none()
            total_days = att_qs.count()
            present_days = att_qs.filter(status='present').count()
            attendance_pct = round((present_days / total_days) * 100, 1) if total_days > 0 else None

            total_assignments = Assignment.objects.filter(batch=batch).count() if batch else 0
            submitted = AssignmentSubmission.objects.filter(student=student, assignment__batch=batch).count() if batch else 0

            session = MockInterviewSession.objects.filter(student=student, batch=batch).first() if batch else None

            results.append({
                'id': student.id,
                'username': student.username,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'profile_photo': student.profile_photo,
                'personal_email': student.personal_email,
                'official_email': student.official_email,
                'phone': student.phone,
                'batch_id': batch.id if batch else None,
                'batch_name': batch.name if batch else None,
                'trainer_username': batch.trainer.username if batch else None,
                'trainer_first_name': batch.trainer.first_name if batch else None,
                'trainer_last_name': batch.trainer.last_name if batch else None,
                'course_name': (batch.course_name or batch.name) if batch else None,
                'batch_status': batch.status if batch else None,
                'attendance_percentage': attendance_pct,
                'assignments_submitted': submitted,
                'total_assignments': total_assignments,
                'mock_interview_status': (
                    'Not invited' if not session
                    else 'Scored' if session.score is not None
                    else 'Attended' if session.attended
                    else 'Missed' if session.attended is False
                    else 'Invited'
                ),
            })

        return Response(results)  


class TrainerListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.filter(role='trainer', is_superuser=False, is_staff=False)    

from .serializers import CreateTrainerSerializer


class CreateTrainerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        serializer = CreateTrainerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trainer = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            email=data['email'],
            role='trainer',
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
        )

        return Response({
            "detail": "Trainer account created.",
            "username": trainer.username,
            "email": trainer.email,
        }, status=201)

class TrainerDirectoryView(APIView):
    """Full trainer directory for founder/business team — shows each
    trainer's batch count, total students, and ongoing/completed split."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from trainer_ai.models import Batch, Attendance

        user = request.user
        if user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        results = []
        for trainer in User.objects.filter(role='trainer', is_superuser=False, is_staff=False).order_by('username'):
            batches = Batch.objects.filter(trainer=trainer)
            ongoing_count = batches.filter(status='ongoing').count()
            completed_count = batches.filter(status='completed').count()

            student_ids = Attendance.objects.filter(batch__trainer=trainer).values_list('student_id', flat=True).distinct()

            results.append({
                'id': trainer.id,
                'username': trainer.username,
                'first_name': trainer.first_name,
                'last_name': trainer.last_name,
                'email': trainer.email,
                'phone': trainer.phone,
                'profile_photo': trainer.profile_photo,
                'batch_count': batches.count(),
                'ongoing_count': ongoing_count,
                'completed_count': completed_count,
                'student_count': len(set(student_ids)),
            })

        return Response(results)    

class TrainerDetailView(APIView):
    """Full detail for one trainer — all their batches with enrollment,
    syllabus progress, and status."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, trainer_id):
        from trainer_ai.models import Batch, Attendance, LessonPlan

        user = request.user
        if user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        try:
            trainer = User.objects.get(id=trainer_id, role='trainer')
        except User.DoesNotExist:
            return Response({"detail": "Trainer not found."}, status=404)

        batches = Batch.objects.filter(trainer=trainer).order_by('-created_at')
        batch_rows = []
        for batch in batches:
            student_ids = Attendance.objects.filter(batch=batch).values_list('student_id', flat=True).distinct()
            topics_covered = LessonPlan.objects.filter(batch=batch).values_list('topic', flat=True).distinct().count()

            batch_rows.append({
                'id': batch.id,
                'name': batch.name,
                'course_name': batch.course_name,
                'status': batch.status,
                'start_date': batch.start_date,
                'end_date': batch.end_date,
                'students_enrolled': len(set(student_ids)),
                'max_students': batch.max_students,
                'topics_covered': topics_covered,
                'training_mode': batch.training_mode,
            })

        return Response({
            'trainer': {
                'id': trainer.id,
                'username': trainer.username,
                'first_name': trainer.first_name,
                'last_name': trainer.last_name,
                'email': trainer.email,
                'phone': trainer.phone,
                'profile_photo': trainer.profile_photo,
                'tenth_marksheet_url': trainer.tenth_marksheet.url if trainer.tenth_marksheet else None,
                'twelfth_marksheet_url': trainer.twelfth_marksheet.url if trainer.twelfth_marksheet else None,
                'degree_certificate_url': trainer.degree_certificate.url if trainer.degree_certificate else None,
                'pg_certificate_url': trainer.pg_certificate.url if trainer.pg_certificate else None,
                'experience_certificate_url': trainer.experience_certificate.url if trainer.experience_certificate else None,
            },
            'batches': batch_rows,
            'total_batches': len(batch_rows),
            'ongoing_count': sum(1 for b in batch_rows if b['status'] == 'ongoing'),
            'completed_count': sum(1 for b in batch_rows if b['status'] == 'completed'),
        })    


class UploadUserDocumentView(APIView):
    """Business team uploads a document (certificate/T&C) for ANY student or
    trainer by id — not the logged-in user's own upload."""
    permission_classes = [permissions.IsAuthenticated]

    FIELD_MAP = {
        'tenth': 'tenth_marksheet',
        'twelfth': 'twelfth_marksheet',
        'degree': 'degree_certificate',
        'pg': 'pg_certificate',
        'terms': 'terms_conditions_doc',
        'experience': 'experience_certificate',
    }

    def post(self, request, user_id):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        doc_type = request.data.get('doc_type')
        file = request.FILES.get('file')

        if doc_type not in self.FIELD_MAP:
            return Response({"detail": f"doc_type must be one of: {', '.join(self.FIELD_MAP.keys())}."}, status=400)
        if not file:
            return Response({"detail": "No file provided."}, status=400)
        if not file.name.lower().endswith('.pdf'):
            return Response({"detail": "Only PDF files are accepted."}, status=400)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        field_name = self.FIELD_MAP[doc_type]
        setattr(target_user, field_name, file)
        target_user.save()

        return Response(UserSerializer(target_user).data)    


from .serializers import UpdateOfficialEmailSerializer


class UpdateOfficialEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, user_id):
        if request.user.role not in ('admin', 'management'):
            return Response({"detail": "Not authorized."}, status=403)

        serializer = UpdateOfficialEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        target_user.official_email = serializer.validated_data['official_email']
        target_user.save()  # triggers your existing sync: official_email → login email

        return Response(UserSerializer(target_user).data)    