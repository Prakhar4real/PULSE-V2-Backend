from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

#1. USER PROFILE
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    level = models.CharField(max_length=50, default="Scout")
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def save(self, *args, **kwargs):
        # Auto-calculate Level
        if self.points >= 500: self.level = "Hero"
        elif self.points >= 300: self.level = "Guardian"
        elif self.points >= 100: self.level = "Scout"
        else: self.level = "Citizen"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

#2. REPORT INCIDENT
class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), 
        ('verified', 'Verified'), 
        ('rejected', 'Rejected'), 
        ('resolved', 'Resolved')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100, default="Infrastructure")
    location = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    # Image Fields
    image = models.ImageField(upload_to='reports/', max_length=500, blank=True, null=True)
    resolved_image = models.ImageField(upload_to='resolved_proofs/', max_length=500, blank=True, null=True)
    
    # Geo Data
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Status & Feedback
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True, null=True)
    rating = models.IntegerField(default=0)
    
    # AI Data
    ai_analysis = models.TextField(blank=True, null=True)
    ai_confidence = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

#3. MISSIONS
class Mission(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    points_reward = models.IntegerField(default=50) 
    icon = models.CharField(max_length=50, default="🏆") 

    def __str__(self):
        return self.title

class UserMission(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('completed', 'Completed')]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    submitted_at = models.DateTimeField(auto_now=True, null=True)

    proof_image = models.ImageField(upload_to='mission_proofs/', max_length=500, null=True, blank=True)
    ai_analysis = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.mission.title}"

#4. COMMUNITY NOTICES
class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

#5. SIGNALS
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # Just ensure it exists
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()