from django.db import models
from django.contrib.auth.models import User
import google.generativeai as genai
from decouple import config
from PIL import Image

# --- CONFIGURE GEMINI AI ---
GEMINI_API_KEY = config('GEMINI_API_KEY', default=None)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- HELPER: Auto-Select Best Model ---
def get_best_model():
    """
    Dynamically finds the best available Gemini model.
    Prioritizes 'flash' for speed, then falls back to 'pro'.
    """
    try:
        if not GEMINI_API_KEY:
            return None
            
        # List all models that support generating content
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 1. Look for the generic "latest" alias first (Best for future-proofing)
        if 'models/gemini-flash-latest' in available_models:
            return genai.GenerativeModel('gemini-flash-latest')
            
        # 2. Look for specific Flash versions (2.0, 1.5, etc.)
        flash_models = [m for m in available_models if 'flash' in m]
        if flash_models:
            # Sort to get the highest version number (e.g., 2.0 > 1.5)
            best_flash = sorted(flash_models)[-1] 
            return genai.GenerativeModel(best_flash)

        # 3. Fallback to any generic model
        return genai.GenerativeModel('gemini-pro')

    except Exception as e:
        print(f"Model Selection Error: {e}")
        return None

# --- 1. USER PROFILE ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    level = models.CharField(max_length=50, default="Scout")
    phone_number = models.CharField(max_length=15, blank=True, null=True)

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
    
    # AI Fields
    ai_analysis = models.TextField(blank=True, null=True)
    ai_confidence = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

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
                if "true" in response.text.lower():
                    self.ai_confidence = 90
                    self.status = 'verified'
                else:
                    self.ai_confidence = 10
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