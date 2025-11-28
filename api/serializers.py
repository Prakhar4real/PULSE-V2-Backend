from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Report  # <--- Import model

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

# --- ADD THIS NEW CLASS BELOW ---
class ReportSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username') # Show username, don't ask for ID

    class Meta:
        model = Report
        fields = ['id', 'username', 'title', 'description', 'city', 'latitude', 'longitude', 'image', 'status', 'created_at']
        extra_kwargs = {'image': {'required': False}} # Image is optional