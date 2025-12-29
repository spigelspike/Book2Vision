import os
from pathlib import Path
from dotenv import load_dotenv

# Force load from absolute path to ensure we find the .env file
env_path = Path(__file__).parent.parent / '.env'
print(f"Loading .env from: {env_path}")
print(f"File exists: {env_path.exists()}")

load_dotenv(dotenv_path=env_path, override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
BYTEZ_API_KEY = os.getenv("BYTEZ_API_KEY")

# Debug print (masked)
if OPENROUTER_API_KEY:
    print(f"✅ OPENROUTER_API_KEY loaded: {OPENROUTER_API_KEY[:5]}...{OPENROUTER_API_KEY[-4:]}")
else:
    print("❌ OPENROUTER_API_KEY NOT FOUND in environment")
    # Try manual read as fallback
    try:
        if env_path.exists():
            print("Attempting manual read of .env...")
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('OPENROUTER_API_KEY='):
                        key = line.strip().split('=', 1)[1].strip()
                        # Remove quotes if present
                        if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
                            key = key[1:-1]
                        OPENROUTER_API_KEY = key
                        print(f"✅ Manually extracted OPENROUTER_API_KEY: {OPENROUTER_API_KEY[:5]}...")
                        break
    except Exception as e:
        print(f"Manual read failed: {e}")

# Audio Settings
TTS_VOICE = "en-US-ChristopherNeural" # High quality male voice
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

# Visual Settings
IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "standard"
