from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from django.core.files.base import ContentFile
from io import BytesIO
from reportlab.pdfgen import canvas

from .models import User, Request
from .serializers import UserSerializer, RequestSerializer

# ------------------------
# User Signup
# ------------------------
class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "user": UserSerializer(user).data,
                "token": token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ------------------------
# User Login
# ------------------------
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "user": UserSerializer(user).data,
                "token": token.key
            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)


# ------------------------
# Current User
# ------------------------
class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ------------------------
# Requests List / Create
# ------------------------
class RequestListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == 'staff':
            requests = Request.objects.filter(created_by=user)
        elif user.role == 'approver':
            requests = Request.objects.filter(status='PENDING')
        elif user.role == 'finance':
            requests = Request.objects.filter(status='APPROVED')
        else:
            requests = Request.objects.none()
        serializer = RequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != 'staff':
            return Response({"error": "Only staff can create purchase requests"}, status=status.HTTP_403_FORBIDDEN)

        serializer = RequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ------------------------
# Request Detail / Update
# ------------------------
class RequestDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        return Request.objects.filter(pk=pk).first()

    def get(self, request, pk):
        request_obj = self.get_object(pk)
        if not request_obj:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(RequestSerializer(request_obj).data)

    def put(self, request, pk):
        request_obj = self.get_object(pk)
        if not request_obj:
            return Response({"error": "Not found"}, status=404)

        if request.user.role != 'staff':
            return Response({"error": "Only staff can update requests"}, status=403)

        if request_obj.created_by != request.user:
            return Response({"error": "You cannot modify this request"}, status=403)

        if request_obj.status != 'PENDING':
            return Response({"error": "Cannot update a reviewed request"}, status=400)

        serializer = RequestSerializer(request_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# ------------------------
# Approve Request
# ------------------------
class ApproveRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != 'approver':
            return Response({"error": "Only approvers can approve requests"}, status=403)

        request_obj = Request.objects.filter(pk=pk).first()
        if not request_obj:
            return Response({"error": "Request not found"}, status=404)

        if request_obj.status != 'PENDING':
            return Response({"error": "Request already reviewed"}, status=400)

        request_obj.status = "APPROVED"
        request_obj.approved_by = request.user

        if request_obj.proforma and not request_obj.purchase_order:
            buffer = BytesIO()
            p = canvas.Canvas(buffer)
            p.drawString(100, 750, f"Purchase Order for Request #{request_obj.pk}")
            p.drawString(100, 720, f"Title: {request_obj.title}")
            p.drawString(100, 700, f"Description: {request_obj.description}")
            p.drawString(100, 680, f"Amount: ${request_obj.amount}")
            p.drawString(100, 660, f"Created By: {request_obj.created_by.username}")
            p.drawString(100, 640, f"Approved By: {request_obj.approved_by.username}")
            p.showPage()
            p.save()
            buffer.seek(0)
            file_name = f'PO_{request_obj.pk}.pdf'
            request_obj.purchase_order.save(file_name, ContentFile(buffer.read()), save=False)
            buffer.close()

        request_obj.save()
        return Response(RequestSerializer(request_obj).data)


# ------------------------
# Reject Request
# ------------------------
class RejectRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != 'approver':
            return Response({"error": "Only approvers can reject requests"}, status=403)

        request_obj = Request.objects.filter(pk=pk).first()
        if not request_obj:
            return Response({"error": "Request not found"}, status=404)

        if request_obj.status != 'PENDING':
            return Response({"error": "Request already reviewed"}, status=400)

        request_obj.status = "REJECTED"
        request_obj.approved_by = request.user
        request_obj.save()
        return Response(RequestSerializer(request_obj).data)


# ------------------------
# Finance Upload Receipt
# ------------------------
class UploadReceiptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != 'finance':
            return Response({"error": "Only finance can upload receipt"}, status=403)

        request_obj = Request.objects.filter(pk=pk, status='APPROVED').first()
        if not request_obj:
            return Response({"error": "Approved request not found"}, status=404)

        receipt_file = request.FILES.get('receipt')
        if not receipt_file:
            return Response({"error": "No receipt file provided"}, status=400)

        request_obj.receipt = receipt_file
        request_obj.save()
        return Response(RequestSerializer(request_obj).data)


# ------------------------
# Filtered Request List (Pending)
# ------------------------
class FilteredRequestListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == 'approver':
            requests = Request.objects.filter(status='PENDING')
        elif user.role == 'finance':
            requests = Request.objects.filter(status='APPROVED')
        else:
            requests = Request.objects.none()
        serializer = RequestSerializer(requests, many=True)
        return Response(serializer.data)


# ------------------------
# Reviewed Request List (Approved or Rejected)
# ------------------------
class ReviewedRequestListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requests = Request.objects.filter(status__in=['APPROVED', 'REJECTED'])
        serializer = RequestSerializer(requests, many=True)
        return Response(serializer.data)
    
    
# ------------------------
# User Logout
# ------------------------
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Deletes the current user's token so they are logged out.
        """
        try:
            request.user.auth_token.delete()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
