from django.urls import path
from .views import (
    CourseListView, EnquiryCreateView, EnquiryListView,
    EnquiryUpdateStatusView, CourseViewSet, CourseDetailView,PaymentsListView, InvoiceDownloadView, EnquiriesWithoutPaymentView,
    NewEnquiryCountView, MarkEnquiriesSeenView, DeletePaymentView
)
from .views import PaymentCreateView, PaymentDetailView, MarkInstallmentPaidView
from .views import SuggestUsernameView, CreateAccountView
from .views import UngroupedStudentsView, GroupIntoBatchView
from .views import WelcomeKitDetailView, WelcomeKitUpdateView

urlpatterns = [
    path('courses/', CourseViewSet.as_view(), name='courses'),
    path('courses/public/', CourseListView.as_view(), name='courses-public'),
    path('courses/<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    path('enquiries/', EnquiryListView.as_view(), name='enquiries'),
    path('enquiries/submit/', EnquiryCreateView.as_view(), name='enquiry-submit'),
    path('enquiries/<int:pk>/status/', EnquiryUpdateStatusView.as_view(), name='enquiry-status'),
    path('payments/create/', PaymentCreateView.as_view(), name='payment-create'),
    path('payments/enquiry/<int:enquiry_id>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('installments/<int:pk>/mark-paid/', MarkInstallmentPaidView.as_view(), name='installment-mark-paid'),
    path('enquiries/<int:enquiry_id>/suggest-username/', SuggestUsernameView.as_view(), name='suggest-username'),
    path('accounts/create/', CreateAccountView.as_view(), name='create-account'),
    path('students/ungrouped/', UngroupedStudentsView.as_view(), name='ungrouped-students'),
    path('batches/group/', GroupIntoBatchView.as_view(), name='group-into-batch'),
    path('welcome-kit/enquiry/<int:enquiry_id>/', WelcomeKitDetailView.as_view(), name='welcome-kit-detail'),
    path('welcome-kit/<int:pk>/update/', WelcomeKitUpdateView.as_view(), name='welcome-kit-update'),
    path('payments/', PaymentsListView.as_view(), name='payments-list'),
    path('payments/<int:enquiry_id>/invoice/', InvoiceDownloadView.as_view(), name='payment-invoice'),
    path('payments/pending-setup/', EnquiriesWithoutPaymentView.as_view(), name='payments-pending-setup'),
    path('enquiries/new-count/', NewEnquiryCountView.as_view(), name='enquiries-new-count'),
    path('enquiries/mark-seen/', MarkEnquiriesSeenView.as_view(), name='enquiries-mark-seen'),
    path('payments/<int:payment_id>/delete/', DeletePaymentView.as_view(), name='payment-delete'),
]