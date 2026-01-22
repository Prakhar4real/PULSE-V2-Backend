from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from django.contrib.auth.models import User
from decouple import config
import google.generativeai as genai
from twilio.rest import Client
from .models import Report, Profile, Mission, UserMission, Notice

# Import models and serializers
from .models import Report, Profile, Mission, UserMission
from .serializers import (
    UserSerializer, 
    RegisterSerializer, 
    ReportSerializer, 
    MissionSerializer, 
    UserMissionSerializer,
    LeaderboardSerializer,
    NoticeSerializer
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


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            return Response({
                "username": user.username, 
                "points": user.profile.points, 
                "level": user.profile.level,
                "phone": user.profile.phone_number,
                "is_staff": user.is_staff
            })
        except Exception:
            return Response({"username": user.username, "points": 0, "level": "N/A"})


# ==========================================
#  2. REPORT & TWILIO VIEWS
# ==========================================

class ReportListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Report.objects.all().order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("\nVALIDATION ERROR:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)

        # Add Points
        try:
            profile = self.request.user.profile
            profile.points += 10
            profile.save()
        except Exception as e:
            print(f"Error updating points: {e}")

        # Send SMS
        sid = config('TWILIO_ACCOUNT_SID', default=None)
        token = config('TWILIO_AUTH_TOKEN', default=None)
        twilio_phone = config('TWILIO_PHONE_NUMBER', default=None)
        admin_phone = "+919305031932" 

        if sid and token:
            try:
                client = Client(sid, token)
                
                # Send to User
                if hasattr(self.request.user, 'profile') and self.request.user.profile.phone_number:
                    client.messages.create(
                        body=f"PULSE: Hi {self.request.user.username}, your report '{instance.title}' has been received! AI Status: {instance.status}",
                        from_=twilio_phone,
                        to=self.request.user.profile.phone_number
                    )

                # Send to Admin
                client.messages.create(
                    body=f"ADMIN ALERT: New Issue '{instance.title}' reported by {self.request.user.username}. AI Confidence: {instance.ai_confidence}%",
                    from_=twilio_phone,
                    to=admin_phone
                )
                print("SMS sent successfully!")

            except Exception as e:
                print(f"SMS Error: {e}")


class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)


class ReportDeleteView(generics.DestroyAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)


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

        model_names = [
            'gemini-2.5-flash',
            'gemini-flash-latest',
        ]
        
        response_text = "I am having trouble connecting to the neural network."

        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(context)
                response_text = response.text
                print(f"Success! Connected to: {model_name}") 
                break 
            except Exception as e:
                print(f"ERROR with {model_name}: {e}") 
                continue

        return Response({"response": response_text})


# ==========================================
#  4. GAMIFICATION VIEWSET (Merged & Correct)
# ==========================================

class GamificationViewSet(viewsets.ViewSet):
    """
    Handles Leaderboard and Mission logic
    """
    permission_classes = [permissions.IsAuthenticated]

    # 1. LEADERBOARD ACTION
    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        # Get top 10 users sorted by points (Highest first)
        top_users = Profile.objects.select_related('user').order_by('-points')[:10]
        serializer = LeaderboardSerializer(top_users, many=True)
        return Response(serializer.data)

    # 2. MISSIONS ACTION
    @action(detail=False, methods=['get'])
    def missions(self, request):
        # A. Get all missions
        all_missions = Mission.objects.all()
        # B. Get missions this user has interacted with
        user_progress = UserMission.objects.filter(user=request.user)
        
        # C. Combine them manually to send "Status" to frontend
        mission_list = []
        for mission in all_missions:
            # Find if user has started this mission
            progress = user_progress.filter(mission=mission).first()
            status = progress.status if progress else "available"
            
            mission_list.append({
                "id": mission.id,
                "title": mission.title,
                "description": mission.description,
                "points": mission.points_reward,
                "icon": mission.icon,
                "status": status # 'available', 'pending', or 'completed'
            })
            
        return Response(mission_list)

    # 3. JOIN ACTION
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        Allows a user to start a mission.
        """
        try:
            mission = Mission.objects.get(pk=pk)
            # Create the entry if it doesn't exist yet
            user_mission, created = UserMission.objects.get_or_create(
                user=request.user,
                mission=mission,
                defaults={'status': 'pending'}
            )
            
            if created:
                return Response({'status': 'joined', 'message': f'Mission "{mission.title}" started!'})
            else:
                return Response({'status': 'already_joined', 'message': 'You are already on this mission!'})
                
        except Mission.DoesNotExist:
            return Response({'error': 'Mission not found'}, status=404)
        
        

    # 4. SUBMIT PROOF ACTION
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def submit_proof(self, request, pk=None):
        print(f"Received proof submission for Mission ID: {pk}")
        
        try:
            # 1. Get Mission & User Progress
            mission = Mission.objects.get(pk=pk)
            user_mission = UserMission.objects.get(user=request.user, mission=mission)
            
            # 2. Get Image
            image = request.data.get('image')
            if not image:
                print("No image found in request data.")
                return Response({'error': 'No image uploaded'}, status=400)

            # 3. RUN AI ANALYSIS (With Crash Protection)
            print(f"Sending to Gemini: {image}")
            
            try:
                # Import here to avoid circular import issues
                from .utils import ai_verify_image 
                match, confidence, reason = ai_verify_image(image, mission.description)
                print(f"AI Result: Match={match}, Conf={confidence}, Reason={reason}")
            except Exception as e:
                print(f"AI CRASHED: {e}")
                return Response({'error': f"AI Service Error: {str(e)}"}, status=500)

            # 4. SAVE RESULTS TO DATABASE (Crucial for Admin Panel)
            user_mission.proof_image = image
            user_mission.ai_analysis = f"Confidence: {confidence}% | Reason: {reason}"
            
            if match and confidence > 75: # Lowered slightly for testing
                user_mission.status = 'completed'
                user_mission.save()
                
                # Give Points
                profile = request.user.profile
                profile.points += mission.points_reward
                profile.save()
                
                return Response({
                    'status': 'verified', 
                    'message': f'Verified! You earned {mission.points_reward} XP!',
                    'reason': reason
                })
            else:
                # Save the rejection so Admin can see WHY
                user_mission.save() 
                return Response({
                    'status': 'rejected', 
                    'message': f'AI Rejection: {reason}',
                    'reason': reason
                })

        except Mission.DoesNotExist:
            return Response({'error': 'Mission not found'}, status=404)
        except UserMission.DoesNotExist:
            return Response({'error': 'You need to join this mission first!'}, status=400)
        except Exception as e:
            print(f"🔥 SERVER CRASH: {e}")
            return Response({'error': str(e)}, status=500)
        

class NoticeListCreateView(generics.ListCreateAPIView):
    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        # Show Pinned notices first, then newest ones
        return Notice.objects.all().order_by('-is_pinned', '-created_at')

    def perform_create(self, serializer):
        # Automatically set the logged-in user as the author
        serializer.save(author=self.request.user)        