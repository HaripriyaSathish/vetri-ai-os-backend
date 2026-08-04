from google import genai
from decouple import config

_client = genai.Client(api_key=config('GEMINI_API_KEY'))

def ask_claude(prompt: str, max_tokens: int = 3000) -> str:
    """
    Sends a prompt to Gemini and returns the plain text response.
    Kept the name 'ask_claude' so every other file (ai_views.py, future agents)
    doesn't need to change if we switch providers again later.
    """
    response = _client.models.generate_content(
        model='gemini-flash-latest',
        contents=prompt,
        config={'max_output_tokens': max_tokens},
    )
    return response.text