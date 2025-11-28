from django.contrib.auth.models import User
from rest_framework import generics, permissions
from .serializers import UserSerializer, ReportSerializer # Import ReportSerializer
from .models import Report # Import Report Model
from rest_framework.permissions import AllowAny, IsAuthenticated

# ... (Keep your CreateUserView here) ...
class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

# --- ADD THESE NEW VIEWS BELOW ---

# ... imports
from .models import Report, Profile # Import Profile

class ReportListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # --- CHANGE IS HERE ---
        return Report.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        # Add points logic...
        profile = self.request.user.profile
        profile.points += 10
        profile.save()

class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    # This handles Get One, Update, and Delete
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only delete/update THEIR OWN reports
        return Report.objects.filter(user=self.request.user)
    
    # ... other imports
from rest_framework.views import APIView
from rest_framework.response import Response

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "username": user.username,
            "points": user.profile.points,
            "level": user.profile.level
        })