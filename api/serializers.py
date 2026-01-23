from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Report, Profile, Mission, UserMission
from .utils import ai_verify_image
from .models import Notice

class NoticeSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'author_name', 'is_pinned', 'created_at']

# 1. USER REGISTRATION SERIALIZER
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )
        return user

# 2. STANDARD USER SERIALIZER
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

# 3. REPORT SERIALIZER (With AI Logic)
class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ["user", "status", "created_at", "ai_analysis", "ai_confidence"]

    def create(self, validated_data):
        # 1. Get the image and description
        image = validated_data.get('image')
        description = validated_data.get('description', '')
        
        # 2. Run AI Verification (if image exists)
        ai_status = "Pending"
        ai_confidence = 0
        ai_reason = "No image uploaded"
        final_status = "pending"

        if image:
            print("AI is analyzing the evidence...")
            # Calls the utility function 
            match, confidence, reason = ai_verify_image(image, description)
            
            ai_confidence = confidence
            ai_reason = reason
            
            # --- THE DECISION LOGIC ---
            if match and confidence > 85:
                print(f"AI Verified! ({confidence}%) Auto-approving.")
                ai_status = "Verified"
                final_status = "verified" # AUTO-APPROVE!
            else:
                print(f"AI Unsure ({confidence}%). Sent to Admin.")
                ai_status = "Flagged"
                final_status = "pending" # Keep pending for Admin

        # 3. Save to Database
        report = Report.objects.create(
            **validated_data,
            status=final_status,
            ai_analysis=ai_reason,     # Save the AI's explanation
            ai_confidence=ai_confidence # Save the score (0-100)
        )
        return report

# 4. GAMIFICATION SERIALIZERS 

class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = '__all__'

class UserMissionSerializer(serializers.ModelSerializer):
    mission_title = serializers.ReadOnlyField(source='mission.title')

    class Meta:
        model = UserMission
        
        fields = ['id', 'mission', 'mission_title', 'status', 'submitted_at']
        read_only_fields = ['status', 'submitted_at']

class LeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    
    class Meta:
        model = Profile
        fields = ['username', 'points', 'level']

        