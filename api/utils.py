import google.generativeai as genai
from decouple import config
import PIL.Image  # <--- THIS IS THE MISSING KEY 🔑
import json

genai.configure(api_key=config('GEMINI_API_KEY'))

def ai_verify_image(image, description="General anomaly"):
    """
    Analyzes an image to see if it matches the provided description.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # Or 'gemini-flash-latest'

        
        prompt = (
            f"The user has uploaded this image as proof for a task described as: '{description}'. "
            "Ignore any mentions of points, XP, rewards, or game mechanics in the description. "
            "Focus ONLY on the physical objects or actions. "
            "Does the visual content of the image match the core task described? "
            "Return JSON with 'match' (true/false), 'confidence' (0-100), and 'reason'."
        
        )

        # Open image correctly
        img = PIL.Image.open(image)
        
        response = model.generate_content([prompt, img])
        response_text = response.text.lower()

        # Clean up JSON formatting if Gemini adds backticks
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        import json
        data = json.loads(response_text)
        
        return data.get('match', False), data.get('confidence', 0), data.get('reason', "AI could not decide.")

    except Exception as e:
        print(f"AI Error: {e}")
        return False, 0, f"AI Error: {str(e)}"