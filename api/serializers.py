from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Report, Profile, Mission, UserMission, Notice

#1. NOTICE SERIALIZER
class NoticeSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Notice
        fields = ['id', 'title', 'content', 'author_name', 'is_pinned', 'created_at']

#2. USER REGISTRATION SERIALIZER
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'phone_number')

    def create(self, validated_data):
        phone = validated_data.pop('phone_number', None)
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )
        if phone:
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone_number = phone
            profile.save()
        return user

#3. STANDARD USER SERIALIZER
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

#4. USER PROFILE SERIALIZER
class ProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'user_id', 'username', 'email', 'bio', 'phone_number', 'profile_picture']

#5. REPORT SERIALIZER
class ReportSerializer(serializers.ModelSerializer):
    
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = Report
        fields = [
            'id', 'user', 'title', 'description', 'category', 
            'image', 'location', 'latitude', 'longitude', 
            'status', 'created_at', 'ai_analysis', 'ai_confidence',
            'resolved_image', 'feedback' 
        ]
        # These are read-only for the user, but the View can update them
        read_only_fields = ["user", "status", "created_at", "ai_analysis", "ai_confidence"]

# 6. GAMIFICATION SERIALIZERS
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
    profile_picture = serializers.ImageField(read_only=True) 

    class Meta:
        model = Profile
        fields = ['username', 'points', 'level', 'profile_picture']