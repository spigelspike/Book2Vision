import os
from pathlib import Path
from dotenv import load_dotenv

# Force load from absolute path to ensure we find the .env file
env_path = Path(__file__).parent.parent / '.env'
print(f"Loading .env from: {env_path}")
print(f"File exists: {env_path.exists()}")

load_dotenv(dotenv_path=env_path, override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEY", "").split(",") if k.strip()]
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
BYTEZ_API_KEY = os.getenv("BYTEZ_API_KEY")
DEAPI_API_KEY = os.getenv("DEAPI_API_KEY")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
PODCAST_API_KEYS = [k.strip() for k in os.getenv("PODCAST_API_KEY", "").split(",") if k.strip()]

# Primary keys for backward compatibility
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else None
PODCAST_API_KEY = PODCAST_API_KEYS[0] if PODCAST_API_KEYS else None

def get_allocated_keys(purpose="general"):
    """
    Returns a prioritized list of keys for a specific purpose.
    Distributes load across the 3 Gemini keys and the Podcast key.
    """
    if not GEMINI_API_KEYS:
        return PODCAST_API_KEYS
        
    g1 = [GEMINI_API_KEYS[0]] if len(GEMINI_API_KEYS) > 0 else []
    g2 = [GEMINI_API_KEYS[1]] if len(GEMINI_API_KEYS) > 1 else g1
    g3 = [GEMINI_API_KEYS[2]] if len(GEMINI_API_KEYS) > 2 else g1
    p = PODCAST_API_KEYS if PODCAST_API_KEYS else g1
    
    if purpose == "analysis":
        return g1 + g2 + g3 + p
    elif purpose == "audio":
        return g2 + g3 + g1 + p
    elif purpose == "knowledge":
        return g3 + g1 + g2 + p
    elif purpose == "podcast":
        # Only use dedicated podcast keys to ensure immediate fallback to OpenRouter if they fail
        return p if p else g1
    else:
        return GEMINI_API_KEYS + PODCAST_API_KEYS

# Debug print (masked)
if OPENROUTER_API_KEY:
    print(f" OPENROUTER_API_KEY loaded: {OPENROUTER_API_KEY[:5]}...{OPENROUTER_API_KEY[-4:]}")
else:
    print(" OPENROUTER_API_KEY NOT FOUND in environment")
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
                        print(f" Manually extracted OPENROUTER_API_KEY: {OPENROUTER_API_KEY[:5]}...")
                        break
    except Exception as e:
        print(f"Manual read failed: {e}")

if PODCAST_API_KEY:
    print(f" PODCAST_API_KEY loaded: {PODCAST_API_KEY[:5]}...{PODCAST_API_KEY[-4:]}")
else:
    print(" PODCAST_API_KEY NOT FOUND in environment")

# Audio Settings
TTS_VOICE = "en-US-ChristopherNeural" # High quality male voice
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

# Visual Settings
IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "standard"
