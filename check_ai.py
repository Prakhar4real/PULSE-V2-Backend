import google.generativeai as genai
from decouple import config

# 1. Setup
api_key = config('GEMINI_API_KEY', default=None)

if not api_key:
    print("Error: GEMINI_API_KEY is missing from .env file")
else:
    genai.configure(api_key=api_key)
    print(f"Key found! Checking available models for key ending in: ...{api_key[-5:]}")

    # 2. List Models
    try:
        print("\n--- AVAILABLE MODELS ---")
        found_any = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"{m.name}")
                found_any = True
        
        if not found_any:
            print("No content generation models found. Check your API Key permissions.")
            
    except Exception as e:
        print(f"\nConnection Error: {e}")