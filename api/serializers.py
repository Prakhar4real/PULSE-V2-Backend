from django.contrib.auth.models import User
from .models import Report, Profile
from .models import Report 
from rest_framework import serializers
from django.db import IntegrityError
from .models import Profile


class UserSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "password", "phone_number"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        # 1. Get the phone number
        phone_raw = validated_data.pop('phone_number', None)
        
        # 2. Create the User 
        user = User.objects.create_user(**validated_data)

        try:
            
            profile = Profile.objects.get(user=user)
            profile.phone_number = phone_raw
            profile.save()
        except Profile.DoesNotExist:
           
            Profile.objects.create(user=user, phone_number=phone_raw)
        
        return user
    
class ReportSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username') # Show username, don't ask for ID

    class Meta:
        model = Report
        fields = ['id', 'username', 'title', 'description', 'city', 'latitude', 'longitude', 'image', 'status', 'created_at']
        extra_kwargs = {'image': {'required': False}} # Image is optional