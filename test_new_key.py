#!/usr/bin/env python3
"""Test the new Gemini API key."""

import google.generativeai as genai

# Test the new key
new_key = "AIzaSyBjgylOeqwDE7_DnZHHvah5RIbh8bTN1Vc"

print("Testing new Gemini API key...")
print(f"Key: {new_key[:10]}...{new_key[-10:]}")

try:
    genai.configure(api_key=new_key)
    models = list(genai.list_models())
    print(f"✅ SUCCESS! Gemini API key is VALID!")
    print(f"Found {len(models)} available models.")
    print("\nFirst 5 models:")
    for model in models[:5]:
        print(f"  - {model.name}")
except Exception as e:
    print(f"❌ FAILED! Error: {e}")
