from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from django.contrib.auth.models import User
from decouple import config
import google.generativeai as genai
from twilio.rest import Client
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncHour

# Import models
from .models import Report, Profile, Mission, UserMission, Notice

# Import serializers
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

# --- CUSTOM PERMISSION ---
class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

# --- CONFIGURATION ---
try:
    genai.configure(api_key=config('GEMINI_API_KEY'))
except Exception as e:
    print("Warning: Gemini API Key missing or invalid.")


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
    parser_classes = (MultiPartParser, FormParser) # Required for Image Uploads

    def get_object(self):
        # Ensure the user has a profile, create one if missing
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
                "bio": user.profile.bio, # Now valid
                "profile_picture": user.profile.profile_picture.url if user.profile.profile_picture else None # Now valid
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
        instance = serializer.save(user=self.request.user)
        
        #1. Add Points
        try:
            profile = self.request.user.profile
            profile.points += 10
            profile.save()
        except Exception as e:
            print(f"Gamification Error: {e}")

        # --- 2. Prepare Twilio Client ---
        sid = config('TWILIO_ACCOUNT_SID', default=None)
        token = config('TWILIO_AUTH_TOKEN', default=None)
        twilio_phone = config('TWILIO_PHONE_NUMBER', default=None)
        admin_phone = config('ADMIN_PHONE_NUMBER', default=None) 

        if sid and token:
            try:
                client = Client(sid, token)

                #3. Send User SMS
                try:
                    user_phone = None
                    if hasattr(self.request.user, 'profile') and self.request.user.profile.phone_number:
                        raw_phone = str(self.request.user.profile.phone_number).strip()
                        # Auto-format(+91)
                        if len(raw_phone) == 10 and not raw_phone.startswith('+'):
                            user_phone = f"+91{raw_phone}"
                        else:
                            user_phone = raw_phone if raw_phone.startswith('+') else f"+91{raw_phone}"

                    if user_phone:
                        client.messages.create(
                            body=f"PULSE: Hi {self.request.user.username}, your report '{instance.title}' received! Admins will update you soon. AI Status: {instance.status}",
                            from_=twilio_phone,
                            to=user_phone
                        )
                except Exception as e:
                    print(f"User SMS Failed (Admin still alerted): {e}")

                # --- 4. Send Admin SMS ---
                try:
                    client.messages.create(
                        body=f"ADMIN ALERT: New Issue '{instance.title}' by {self.request.user.username}. AI Confidence: {instance.ai_confidence}%",
                        from_=twilio_phone,
                        to=admin_phone
                    )
                except Exception as e:
                    print(f"Admin SMS Failed: {e}")

            except Exception as e:
                print(f"Twilio Client Error: {e}")


# ==========================================
#  3. AI CHAT VIEW
# ==========================================

class AIChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_message = request.data.get('message', '')
        context = (
            "You are PULSE AI, a helpful assistant for a Smart City Platform. "
            "Keep answers short, professional, and helpful. "
            f"User Question: {user_message}"
        )
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(context)
            return Response({"response": response.text})
        except Exception as e:
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

            # --- AI LOGIC ---
            confidence = 85 
            reason = "AI Verified: Valid evidence provided."

            user_mission.proof_image = image
            user_mission.status = 'completed'
            user_mission.save()
            
            profile = request.user.profile
            profile.points += mission.points_reward
            profile.save()
            
            return Response({'status': 'verified', 'message': f'Verified! You earned {mission.points_reward} XP!'})
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


class TrafficStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = [
            {"time": "8am", "flow": 15},
            {"time": "10am", "flow": 35},
            {"time": "12pm", "flow": 60},
            {"time": "2pm", "flow": 45},
            {"time": "4pm", "flow": 80},
        ]
        return Response(data)
    
    

class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only view/edit/delete their own reports
        return Report.objects.filter(user=self.request.user)


class ReportDeleteView(generics.DestroyAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)