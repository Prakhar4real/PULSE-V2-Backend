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
from .models import Report, Profile, Mission, UserMission, Notice
from .utils import ai_verify_image  
from google import genai 
from rest_framework.exceptions import ValidationError

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

# CUSTOM PERMISSION
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
        image = self.request.FILES.get('image')
        description = self.request.data.get('description', 'Issue report')
        
        # BACKEND 5MB SIZE CHECK
        if image and image.size > 5 * 1024 * 1024:
            from rest_framework.exceptions import ValidationError # Safe inline import
            raise ValidationError({"error": "Image file size exceeds the 5MB limit. Please upload a smaller file."})
        
        ai_confidence = 0
        ai_summary = "No image provided."
        report_status = "pending" # Default

        if image:
            # Only call the AI ONCE
            match, confidence, reason = ai_verify_image(image, description)
            ai_confidence = confidence
            ai_summary = reason
            
            if confidence == 0:
                # AI CRASHED / RATE LIMIT: Fallback
                report_status = "pending"
                ai_summary = "AI Network Busy. Queued for manual review."
            elif match and confidence >= 70:
                # AI APPROVED
                report_status = "verified"
            else:
                # AI REJECTED
                report_status = "rejected"
            
            if hasattr(image, 'seek'):
                image.seek(0)

        instance = serializer.save(
            user=self.request.user,
            ai_confidence=ai_confidence,
            ai_analysis=ai_summary,
            status=report_status
        )
        
        try:
            profile = self.request.user.profile
            profile.points += 10
            profile.save()
        except Exception as e:
            print(f"Gamification Error: {e}")

        self.send_sms_alerts(instance)

    def send_sms_alerts(self, instance):
        sid = config('TWILIO_ACCOUNT_SID', default=None)
        token = config('TWILIO_AUTH_TOKEN', default=None)
        twilio_phone = config('TWILIO_PHONE_NUMBER', default=None)
        admin_phone = config('ADMIN_PHONE_NUMBER', default=None) 

        if sid and token:
            try:
                client = Client(sid, token)
                
                #1. USER SMS 
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
                        print(f"📱 TWILIO: User SMS sent to {user_phone}")
                    else:
                        print("⚠️ TWILIO: User has no phone number. Skipping User SMS.")
                except Exception as e:
                    print(f"❌ TWILIO USER SMS ERROR: {e}") 

                # --- 2. ADMIN SMS ---
                try:
                    if admin_phone:
                        client.messages.create(
                            body=f"ADMIN ALERT: New Issue '{instance.title}'. AI Confidence: {instance.ai_confidence}%",
                            from_=twilio_phone,
                            to=admin_phone
                        )
                        print(f"TWILIO: Admin SMS sent to {admin_phone}")
                    else:
                        print("⚠️ TWILIO: ADMIN_PHONE_NUMBER is missing in .env")
                except Exception as e:
                    print(f"❌ TWILIO ADMIN SMS ERROR: {e}")

            except Exception as e:
                print(f"Twilio Client Setup Error: {e}")

# ==========================================
#  3. AI CHAT VIEW 
# ==========================================

class AIChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_message = request.data.get('message', '')

        system_prompt = (
    "You are PULSE AI, the official in-app assistant for the PULSE Smart City platform. "
    "PULSE is a gamified civic engagement platform where citizens report local issues "
    "(such as potholes, garbage, broken streetlights, water leaks, or unsafe areas), "
    "complete environmental missions, earn XP, unlock badges, and climb leaderboards "
    "to become top contributors in their city.\n\n"

    "Your primary purpose is to help users understand and use the PULSE app effectively. "
    "You assist users with things such as:\n"
    "- How to report civic issues\n"
    "- How missions work\n"
    "- How XP, badges, and leaderboards function\n"
    "- How verification and feedback work\n"
    "- How to navigate features inside the PULSE platform\n"
    "- Encouraging positive civic participation and community impact\n\n"

    "Behavior Rules:\n"
    "1. Only answer questions related to the PULSE platform, civic reporting, missions, "
    "gamification, or community participation.\n"
    "2. Do NOT act as a general-purpose AI assistant.\n"
    "3. Do NOT generate code, essays, stories, poems, homework solutions, or unrelated content.\n"
    "4. If a user asks something unrelated to PULSE, politely redirect them back to PULSE features.\n"
    "5. Never invent features that do not exist in the app.\n"
    "6. Always prioritize clarity and usefulness for citizens using the app.\n\n"

    "Tone and Style:\n"
    "- Be friendly, encouraging, and community-focused.\n"
    "- Keep answers concise and practical.\n"
    "- Avoid long explanations unless necessary.\n"
    "- Use simple language suitable for everyday users.\n\n"

    "Mission:\n"
    "Encourage users to actively participate in improving their city through responsible "
    "reporting, completing missions, and contributing positively to their community."
)

        context = f"{system_prompt}\n\nUser's Message: {user_message}"

        try:
            api_key = config('GEMINI_API_KEY', default=None)
            if not api_key:
                return Response({"response": "AI Config Missing"}, status=503)

            client = genai.Client(api_key=api_key)
            
            # Use 'gemini-flash-latest' 
            response = client.models.generate_content(
                model='gemini-flash-latest', 
                contents=context
            )
            return Response({"response": response.text})

        except Exception as e:
            print(f"CHATBOT ERROR: {e}")
            if "429" in str(e):
                return Response({"response": "I am currently overloaded. Please try again in 1 minute."}, status=200)
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
            user_mission = UserMission.objects.filter(user=request.user, mission=mission).first()
            
            # NOTE: We only check if they joined, DO NOT block them if it's "completed"
            if not user_mission: 
                return Response({'error': 'Join mission first'}, status=400)
            
            image = request.data.get('image')
            if not image: 
                return Response({'error': 'No image uploaded'}, status=400)

            # 5MB BACKEND SIZE CHECK
            if image.size > 5 * 1024 * 1024:
                return Response({"error": "Image file size exceeds the 5MB limit. Please upload a smaller file."}, status=400)

            # REAL AI LOGIC
            match, confidence, reason = ai_verify_image(image, mission.description)

            if confidence == 0:
                # AI CRASHED / RATE LIMIT: Fallback to Manual Review
                user_mission.status = 'pending'
                message = "AI Network Busy. Queued for human review."
                status_resp = 'pending'

            elif match and confidence >= 70:
                # AI APPROVED: Auto-Accept
                user_mission.status = 'completed'
                profile = request.user.profile
                profile.points += mission.points_reward
                profile.save()
                message = f'Verified! You earned {mission.points_reward} XP!'
                status_resp = 'verified'
                
            else:
                # AI REJECTED: Hard Reject
                user_mission.status = 'rejected' 
                message = f'Proof Rejected by AI: {reason}'
                status_resp = 'failed'

            if hasattr(image, 'seek'):
                image.seek(0)

            # This will overwrite their previous image with the newest one
            user_mission.proof_image = image
            user_mission.ai_analysis = reason
            user_mission.save()
            
            return Response({'status': status_resp, 'message': message, 'confidence': confidence})
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# ==========================================
#  5. NOTICES 
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