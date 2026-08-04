from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, RegisterView, MeView, ForgotPasswordView, ResetPasswordView, StudentListView, UpdateProfileView, UploadAvatarView
from .views import StudentDirectoryView
from .views import UploadCertificateView
from .views import TrainerListView
from .views import CreateTrainerView
from .views import TrainerDirectoryView
from .views import TrainerDetailView
from .views import UploadUserDocumentView
from .views import UpdateOfficialEmailView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('students/', StudentListView.as_view(), name='student-list'),
    path('profile/update/', UpdateProfileView.as_view(), name='update-profile'),
    path('profile/avatar/', UploadAvatarView.as_view(), name='upload-avatar'),
    path('profile/certificate/', UploadCertificateView.as_view(), name='upload-certificate'),
    path('students/directory/', StudentDirectoryView.as_view(), name='student-directory'),
    path('trainers/', TrainerListView.as_view(), name='trainer-list'),
    path('trainers/create/', CreateTrainerView.as_view(), name='create-trainer'),
    path('trainers/directory/', TrainerDirectoryView.as_view(), name='trainer-directory'),
    path('trainers/<int:trainer_id>/', TrainerDetailView.as_view(), name='trainer-detail'),
    path('users/<int:user_id>/upload-document/', UploadUserDocumentView.as_view(), name='upload-user-document'),
    path('users/<int:user_id>/update-official-email/', UpdateOfficialEmailView.as_view(), name='update-official-email'),
]