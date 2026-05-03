from google import genai
import os
from src.config import GEMINI_API_KEY

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    for m in client.models.list():
        print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
