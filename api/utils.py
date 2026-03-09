from google import genai
from decouple import config
import PIL.Image
import json
import time
import re

def ai_verify_image(image, description="General anomaly"):
    print("\n---AI IMAGE VERIFICATION START ---")
    
    api_key = config('GEMINI_API_KEY', default=None)
    if not api_key:
        print("❌ AI ERROR: API Key is missing.")
        return False, 0, "Server Error: API Key missing."

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"❌ AI CLIENT ERROR: {e}")
        return False, 0, "Failed to initialize AI client."

    prompt = (
        f"The user has uploaded this image as proof for completing a mission described as: '{description}'. "
        "Your task is to verify whether the visual content in the image clearly matches this description. "
        "Analyze ONLY what is visibly present in the image. Do not assume context that cannot be seen. "
        "Ignore points, XP, rewards, or any gamification elements. Focus strictly on visual verification. "
        "If the main subject related to the description is clearly visible, mark it as a match. "
        "If the image is blurry, unrelated, unclear, or does not provide sufficient visual evidence, mark it as not a match. "
        "Be conservative: if you are uncertain, return match as false. "
        "Return JSON ONLY with these exact fields: "
        "'match' (boolean indicating whether the image matches the description), "
        "'confidence' (integer between 0 and 100 indicating certainty), "
        "and 'reason' (a short explanation based only on visible evidence in the image). "
        "Do not include any text outside the JSON response."
    )

    # Rewind file to start
    if hasattr(image, 'seek'):
        image.seek(0)
    
    try:
        img = PIL.Image.open(image)
        # FIX 1: Force image to RGB (Gemini crashes on RGBA/transparent images)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        print("✅ Image loaded and converted to RGB successfully.")
    except Exception as e:
        print(f"❌ AI IMAGE FORMAT ERROR: {e}")
        return False, 0, "Invalid image format."

    # explicitly naming the model is usually safer.
    target_model = 'gemini-flash-latest' 
    print(f"🚀 Sending to model: {target_model}...")
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=target_model, 
                contents=[prompt, img]
            )
            
            print(f"📥 RAW AI RESPONSE:\n{response.text}")
            
            # FIX 2: Bulletproof JSON Extractor
            response_text = response.text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                response_text = json_match.group(0)
            else:
                raise ValueError("No JSON object found in the AI response.")

            data = json.loads(response_text)
            
            match = data.get('match', False)
            if isinstance(match, str): match = match.lower() == 'true'
            
            confidence = int(data.get('confidence', 0))
            reason = data.get('reason', "AI processed image.")
            
            if confidence < 70: match = False

            print(f"✅ AI SUCCESS: Match={match}, Confidence={confidence}%")
            return match, confidence, reason

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ AI ERROR (Attempt {attempt+1}): {error_str}")
            
            #Catch both 429 (Rate Limit) AND 503 (Overloaded)
            if "429" in error_str or "503" in error_str:
                print("⏳ AI is rate-limited or overloaded. Retrying...")
                time.sleep(2)
                continue
            else:
                # If it's a completely different error (like a bad API key), fail safely
                return False, 0, f"AI Error: {error_str}"
    
    #If all retries fail, return confidence=0 so it queues for human review
    print("❌ AI FINAL STATUS: Unavailable")
    return False, 0, "AI Network Busy. Queued for manual review."