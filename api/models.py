from django.db import models
from django.contrib.auth.models import User

class Report(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SOLVED', 'Solved'),
    ]

    # Link the report to the User who submitted it
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    city = models.CharField(max_length=50)
    
    # Location Data (For the Map)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Evidence
    image = models.ImageField(upload_to='report_images/', null=True, blank=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.status}"
    
    # ... (Report model is above)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    points = models.IntegerField(default=0)
    level = models.CharField(max_length=50, default="Citizen") # Citizen, Hero, Legend

    def __str__(self):
        return f"{self.user.username} - {self.points} XP"

# --- SIGNAL: Auto-create Profile when User is created ---
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
