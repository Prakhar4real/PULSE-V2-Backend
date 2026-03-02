from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from django.contrib.auth.models import User
from decouple import config
from twilio.rest import Client
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncHour
from rest_framework.decorators import api_view, permission_classes
from .models import get_ai_client, get_best_model_name, Report, Profile, Mission, UserMission, Notice
from .utils import ai_verify_image  

from .serializers import (
    UserSerializer, 
    RegisterSerializer, 
    ReportSerializer, 
    MissionSerializer, 
    UserMissionSerializer,
    LeaderboardSerializer,
    NoticeSerializer,
    ProfileUpdateSerializer 
)

#CUSTOM PERMISSION
class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

# ==========================================
#  1. AUTHENTICATION & USER VIEWS
# ==========================================

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileUpdateSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            return Response({
                "username": user.username, 
                "points": user.profile.points, 
                "level": user.profile.level,
                "phone_number": user.profile.phone_number,
                "is_staff": user.is_staff,
                "bio": user.profile.bio,
                "profile_picture": user.profile.profile_picture.url if user.profile.profile_picture else None
            })
        except Exception:
            return Response({"username": user.username, "points": 0, "level": "N/A"})

# ==========================================
#  2. REPORT & TWILIO VIEWS
# ==========================================

class ReportListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Report.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        # --- FIX: CALL AI BEFORE SAVING ---
        image = self.request.FILES.get('image')
        description = self.request.data.get('description', 'Issue report')
        
        ai_confidence = 0
        ai_summary = "No image provided."
        report_status = "pending"

        if image:
            
            match, confidence, reason = ai_verify_image(image, description)
            ai_confidence = confidence
            ai_summary = reason
            
            if confidence > 80 and not match:
                report_status = "rejected"
            elif match and confidence > 70:
                report_status = "verified"

        # Save with AI Data
        instance = serializer.save(
            user=self.request.user,
            ai_confidence=ai_confidence,
            ai_analysis=ai_summary,
            status=report_status
        )
        
        # Add Points
        try:
            profile = self.request.user.profile
            profile.points += 10
            profile.save()
        except Exception as e:
            print(f"Gamification Error: {e}")

        # Send SMS
        self.send_sms_alerts(instance)

    def send_sms_alerts(self, instance):
        sid = config('TWILIO_ACCOUNT_SID', default=None)
        token = config('TWILIO_AUTH_TOKEN', default=None)
        twilio_phone = config('TWILIO_PHONE_NUMBER', default=None)
        admin_phone = config('ADMIN_PHONE_NUMBER', default=None) 

        if sid and token:
            try:
                client = Client(sid, token)
                # User SMS
                try:
                    user_phone = None
                    if hasattr(self.request.user, 'profile') and self.request.user.profile.phone_number:
                        raw_phone = str(self.request.user.profile.phone_number).strip()
                        if len(raw_phone) == 10 and not raw_phone.startswith('+'):
                            user_phone = f"+91{raw_phone}"
                        else:
                            user_phone = raw_phone if raw_phone.startswith('+') else f"+91{raw_phone}"

                    if user_phone:
                        client.messages.create(
                            body=f"PULSE: Hi {self.request.user.username}, report '{instance.title}' received! AI Status: {instance.status}",
                            from_=twilio_phone,
                            to=user_phone
                        )
                except Exception:
                    pass # Fail silently for user

                # Admin SMS
                try:
                    client.messages.create(
                        body=f"ADMIN ALERT: New Issue '{instance.title}'. AI Confidence: {instance.ai_confidence}%",
                        from_=twilio_phone,
                        to=admin_phone
                    )
                except Exception:
                    pass # Fail silently for admin

            except Exception as e:
                print(f"Twilio Client Error: {e}")

# ==========================================
#  3. AI CHAT VIEW 
# ==========================================

class AIChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_message = request.data.get('message', '')
        context = f"You are PULSE AI. Answer this: {user_message}"

        try:
            # Use the new V2 Client Helper
            client = get_ai_client()
            model_name = get_best_model_name() 
            
            if client:
                response = client.models.generate_content(
                    model=model_name, 
                    contents=context
                )
                return Response({"response": response.text})
            return Response({"response": "AI Config Missing"}, status=503)

        except Exception as e:
            print(f"AI Error: {e}")
            return Response({"response": "AI Service Unavailable"}, status=503)

# ==========================================
#  4. GAMIFICATION VIEWSET
# ==========================================

class GamificationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        top_users = Profile.objects.select_related('user').filter(user__is_staff=False).order_by('-points')[:10]
        serializer = LeaderboardSerializer(top_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def missions(self, request):
        all_missions = Mission.objects.all()
        user_progress = UserMission.objects.filter(user=request.user)
        
        mission_list = []
        for mission in all_missions:
            progress = user_progress.filter(mission=mission).first()
            status = progress.status if progress else "available"
            mission_list.append({
                "id": mission.id,
                "title": mission.title,
                "description": mission.description,
                "points": mission.points_reward,
                "icon": mission.icon,
                "status": status 
            })
        return Response(mission_list)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        try:
            mission = Mission.objects.get(pk=pk)
            user_mission, created = UserMission.objects.get_or_create(
                user=request.user, mission=mission, defaults={'status': 'pending'}
            )
            if created:
                return Response({'status': 'joined', 'message': f'Mission "{mission.title}" started!'})
            else:
                return Response({'status': 'already_joined', 'message': 'You are already on this mission!'})
        except Mission.DoesNotExist:
            return Response({'error': 'Mission not found'}, status=404)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def submit_proof(self, request, pk=None):
        try:
            mission = Mission.objects.get(pk=pk)
            user_mission = UserMission.objects.get(user=request.user, mission=mission)
            image = request.data.get('image')
            
            if not image: return Response({'error': 'No image uploaded'}, status=400)

            # REAL AI LOGIC 
            match, confidence, reason = ai_verify_image(image, mission.description)

            if match and confidence > 70:
                user_mission.status = 'completed'
                profile = request.user.profile
                profile.points += mission.points_reward
                profile.save()
                message = f'Verified! You earned {mission.points_reward} XP!'
                status_resp = 'verified'
            else:
                message = f'AI could not verify this proof. Reason: {reason}'
                status_resp = 'failed'

            user_mission.proof_image = image
            user_mission.save()
            
            return Response({'status': status_resp, 'message': message, 'confidence': confidence})
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ==========================================
#  5. NOTICES & TRAFFIC
# ==========================================

class NoticeListCreateView(generics.ListCreateAPIView):
    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Notice.objects.all().order_by('-is_pinned', '-created_at')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)       

class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)

class ReportDeleteView(generics.DestroyAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)
    
@api_view(['GET'])
@permission_classes([AllowAny])
def ping_server(request):
    return Response({"message": "PULSE backend is awake!"})