#!/usr/bin/env python3
"""Test script to verify API keys are loaded correctly."""

import os
from dotenv import load_dotenv

# Force reload
load_dotenv(override=True)

gemini_key = os.getenv("GEMINI_API_KEY")
openrouter_key = os.getenv("OPENROUTER_API_KEY")  
elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")

print("=== API Key Check ===")
print(f"GEMINI_API_KEY: {gemini_key[:10] if gemini_key else 'NOT SET'}...{gemini_key[-10:] if gemini_key and len(gemini_key) > 20 else ''}")
print(f"Length: {len(gemini_key) if gemini_key else 0}")
print()
print(f"OPENROUTER_API_KEY: {openrouter_key[:10] if openrouter_key else 'NOT SET'}...{openrouter_key[-10:] if openrouter_key and len(openrouter_key) > 20 else ''}")
print(f"Length: {len(openrouter_key) if openrouter_key else 0}")
print()
print(f"ELEVENLABS_API_KEY: {elevenlabs_key[:10] if elevenlabs_key else 'NOT SET'}...{elevenlabs_key[-10:] if elevenlabs_key and len(elevenlabs_key) > 20 else ''}")
print(f"Length: {len(elevenlabs_key) if elevenlabs_key else 0}")
print()

# Test Gemini API
if gemini_key:
    print("Testing Gemini API...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        models = list(genai.list_models())
        print(f"✅ Gemini API is working! Found {len(models)} models.")
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
else:
    print("❌ GEMINI_API_KEY not found in environment")
