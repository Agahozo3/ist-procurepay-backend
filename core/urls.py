from django.urls import path
from .views import (
    SignupView, LoginView, CurrentUserView,
    RequestListCreateView, RequestDetailView,
    ApproveRequestView, RejectRequestView,
    UploadReceiptView, FilteredRequestListView,
    ReviewedRequestListView, LogoutView
)

urlpatterns = [
    # Auth
    path("user/auth/signup/", SignupView.as_view(), name="signup"),
    path("user/auth/login/", LoginView.as_view(), name="login"),
    path("user/auth/me/", CurrentUserView.as_view(), name="current_user"),
    path('user/auth/logout/', LogoutView.as_view(), name='logout'),

    # Requests
    path("requests/", RequestListCreateView.as_view(), name="requests_list_create"),
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="request_detail"),
    path("requests/<int:pk>/approve/", ApproveRequestView.as_view(), name="approve_request"),
    path("requests/<int:pk>/reject/", RejectRequestView.as_view(), name="reject_request"),
    path("requests/<int:pk>/submit-receipt/", UploadReceiptView.as_view(), name="submit_receipt"),
    path("requests/filtered/", FilteredRequestListView.as_view(), name="request_filtered"),
    path("requests/reviewed/", ReviewedRequestListView.as_view(), name="requests_reviewed"),
]


