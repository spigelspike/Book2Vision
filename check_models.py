import google.generativeai as genai
import os
from src.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
