from google import genai
from decouple import config
import PIL.Image
import json

def ai_verify_image(image, description="General anomaly"):
    """
    Analyzes an image to see if it matches the provided description.
    Uses Google GenAI V2 SDK.
    """
    try:
        # 1. Initialize Client (V2 Style)
        api_key = config('GEMINI_API_KEY', default=None)
        if not api_key:
            return False, 0, "Server Error: API Key missing."

        client = genai.Client(api_key=api_key)

        # 2. Prepare Prompt
        prompt = (
            f"The user has uploaded this image as proof for a task described as: '{description}'. "
            "Ignore any mentions of points, XP, rewards, or game mechanics in the description. "
            "Focus ONLY on the physical objects or actions. "
            "Does the visual content of the image match the core task described? "
            "Return JSON with 'match' (true/false), 'confidence' (0-100), and 'reason'."
        )

        # 3. Open Image
        # We ensure the image is open and ready for the SDK
        img = PIL.Image.open(image)

        # 4. Generate Content (V2 Syntax)
        # using 'gemini-2.0-flash' which is the current fast standard
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt, img]
        )

        # 5. Parse Response
        response_text = response.text

        # Clean up Markdown
        if "```" in response_text:
            response_text = response_text.replace("```json", "").replace("```", "").strip()

        # Parse JSON
        data = json.loads(response_text)

        # Normalize keys (handle potential case sensitivity)
        match = data.get('match', False)
        # Handle string "true"/"false" if AI messed up boolean
        if isinstance(match, str):
            match = match.lower() == 'true'
            
        return match, data.get('confidence', 0), data.get('reason', "AI processed image.")

    except Exception as e:
        print(f"AI Verification Error: {e}")
        # Return a safe fallback so the server doesn't crash
        return False, 0, f"AI Error: {str(e)}"