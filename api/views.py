from twilio.rest import Client
from rest_framework import generics, permissions, status  
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import UserSerializer, ReportSerializer
from .models import Report, Profile
from decouple import config
import google.generativeai as genai

# Configure API Key
try:
    genai.configure(api_key=config('GEMINI_API_KEY'))
except Exception as e:
    print("Warning: Gemini API Key missing or invalid.")

#(Standard User/Report Views)

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        # Check if valid
        if not serializer.is_valid():
            
            print("\nREGISTRATION FAILED!:")
            print(serializer.errors)
            print("--------------------------------------\n")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ReportListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # 1. Save the Report
        instance = serializer.save(user=self.request.user)

        # 2. Add Points
        try:
            profile = self.request.user.profile
            profile.points += 10
            profile.save()
        except:
            pass

        # 3. SEND SMS ALERTS (User + Admin) 📲
        sid = config('TWILIO_ACCOUNT_SID', default=None)
        token = config('TWILIO_AUTH_TOKEN', default=None)
        twilio_phone = config('TWILIO_PHONE_NUMBER', default=None)
        
        admin_phone = "+919305031932" 

        if sid and token:
            try:
                client = Client(sid, token)
                
                #Send to User
                user_phone = self.request.user.profile.phone_number
                if user_phone:
                    client.messages.create(
                        body=f"✅ PULSE: Hi {self.request.user.username}, your report has been received! We would update you soon.",
                        from_=twilio_phone,
                        to=user_phone
                    )

                #Send to Admin
                # This ensures when a judge/user submits something
                client.messages.create(
                    body=f" ADMIN ALERT: New Issue Reported by {self.request.user.username}.",
                    from_=twilio_phone,
                    to=admin_phone
                )
                print("SMS sent to both User and Admin!")

            except Exception as e:
                print(f"SMS Error: {e}")


class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        try:
            return Response({"username": user.username, "points": user.profile.points, "level": user.profile.level})
        except:
            return Response({"username": user.username, "points": 0, "level": "N/A"})
        

# --- ROBUST AI CHATBOT ---
class ChatBotView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_message = request.data.get('message', '')
        
        # 1. Define Context
        context = (
            "You are PULSE AI, a helpful assistant for a Smart City Platform. "
            "Keep answers short, professional, and helpful. "
            f"User Question: {user_message}"
        )

        # 2. THE SAFETY LIST: Try all these names

        # THE POWER LIST (Prioritized by Intelligence)
        model_names = [
            'models/gemini-3-pro-preview', # 1. The Most Powerful (Experimental)
            'models/gemini-2.5-pro',       # 2. High Intelligence & Stable
            'models/gemini-2.5-flash',     # 3. Super Fast & Efficient
            'models/gemini-2.0-pro-exp',   # 4. Backup Pro
            'gemini-pro'                   # 5. Old Reliable
        ]
        
        response_text = "I am having trouble connecting to the neural network."

        # 3. Try each model until one works
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(context)
                response_text = response.text
                print(f"Success! Connected to: {model_name}") # This will show in terminal
                break # Stop loop, we found a winner
            except Exception as e:
                print(f"ERROR with {model_name}: {e}") 
                continue

        return Response({"response": response_text})