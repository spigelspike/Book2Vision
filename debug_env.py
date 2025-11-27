import os

print("--- Raw .env Content ---")
try:
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, val = line.strip().split("=", 1)
                print(f"{key}={val[:5]}...{val[-5:] if len(val)>10 else ''}")
            else:
                print(f"[Line without =]: {line.strip()}")
except Exception as e:
    print(f"Error reading .env: {e}")

print("\n--- os.environ Content ---")
from dotenv import load_dotenv
load_dotenv(override=True)
for key in ["GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"]:
    val = os.getenv(key)
    if val:
        print(f"{key}={val[:5]}...{val[-5:] if len(val)>10 else ''}")
    else:
        print(f"{key}=NOT SET")
