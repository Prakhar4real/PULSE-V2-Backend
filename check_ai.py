import google.generativeai as genai
from decouple import config

# Load key
try:
    genai.configure(api_key=config('GEMINI_API_KEY'))
    print("✅ API Key loaded.")
except:
    print("❌ Could not load API key. Check .env file.")

print("🔍 Scanning available models...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"👉 Found: {m.name}")