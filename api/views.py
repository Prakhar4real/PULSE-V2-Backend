# api/views.py

from django.contrib.auth.models import User
from rest_framework import generics, permissions
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

# ... (Standard User/Report Views) ...
class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class ReportListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Report.objects.filter(user=self.request.user).order_by('-created_at')
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        try:
            profile = self.request.user.profile
            profile.points += 10
            profile.save()
        except:
            pass

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
                print(f"Success! Connected to: {model_name}") # This will show in your terminal
                break # Stop loop, we found a winner
            except Exception as e:
                print(f"🔴 ERROR with {model_name}: {e}") 
                continue

        return Response({"response": response_text})