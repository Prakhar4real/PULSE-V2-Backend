from django.db import models
from django.contrib.auth.models import User
import google.generativeai as genai
from decouple import config
from PIL import Image
from django.db.models.signals import post_save
from django.dispatch import receiver
from google import genai


# 1. CONFIG
GEMINI_API_KEY = config('GEMINI_API_KEY', default=None)

def get_ai_client():
    """
    Returns the raw Client. 
    You need this to make the actual call.
    """
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)

def get_best_model_name():
    """
    Dynamically scans Google's servers for the newest Flash model.
    Returns a string (e.g., 'gemini-2.0-flash').
    """
    client = get_ai_client()
    if not client:
        return 'gemini-2.0-flash' # Safe fallback

    try:
        # 1. Get list of all available models from Google
        
        all_models = [m.name.replace('models/', '') for m in client.models.list()]

        # 2. Priority: Look for "gemini-flash-latest" 
        if 'gemini-flash-latest' in all_models:
            return 'gemini-flash-latest'

        # 3. Priority: Scan for the highest version of "Flash" (e.g., 2.0 > 1.5)
        flash_models = [m for m in all_models if 'flash' in m]
        if flash_models:
            # Sort alphabetically (works for 1.5 vs 2.0) and take the last one
            return sorted(flash_models)[-1]

        # 4. Fallback: If Flash is missing, try Pro
        pro_models = [m for m in all_models if 'pro' in m]
        if pro_models:
            return sorted(pro_models)[-1]

        # 5. Last Resort
        return 'gemini-2.0-flash'

    except Exception as e:
        print(f"Auto-Detect Error: {e}")
        return 'gemini-2.0-flash'

# --- 1. USER PROFILE ---
from django.db import models
from django.contrib.auth.models import User

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
    


# --- 2. REPORT INCIDENT ---
class Report(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('verified', 'Verified'), ('resolved', 'Resolved')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100, default="Infrastructure")
    location = models.CharField(max_length=255)
    image = models.ImageField(upload_to='reports/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    resolved_image = models.ImageField(upload_to='resolved_proofs/', blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    rating = models.IntegerField(default=0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # AI Fields
    ai_analysis = models.TextField(blank=True, null=True)
    ai_confidence = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Feedback Fields
    resolved_image = models.ImageField(upload_to='resolved_reports/', blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # AI Logic
        if self.image and not self.ai_analysis:
            print("AI: Analyzing image...")
            try:
                
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                img = Image.open(self.image)
                prompt = (
                    f"Analyze this image. Is it related to: {self.description}? "
                    "Return a JSON with keys: 'match' (true/false) and 'confidence' (0-100)."
                )
                response = model.generate_content([prompt, img])
                
                self.ai_analysis = response.text
                if '"match": true' in response.text.lower() or "'match': true" in response.text.lower():
                    self.ai_confidence = 95
                    self.status = 'verified'
                else:
                    self.ai_confidence = 0
                print(f"AI Success: {self.status}")

            except Exception as e:
                print(f"AI Error: {e}")
                self.ai_analysis = f"AI Service Error: {str(e)}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.status})"

# --- 3. MISSIONS ---
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

    proof_image = models.ImageField(upload_to='mission_proofs/', null=True, blank=True)
    ai_analysis = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.mission.title}"
    
    # --- 4. COMMUNITY NOTICES ---
class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_pinned = models.BooleanField(default=False) # Important notices stick to top
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    #Auto-create Profile when User registers
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
   
    try:
        instance.profile.save()
    except Exception:
       
        Profile.objects.create(user=instance)