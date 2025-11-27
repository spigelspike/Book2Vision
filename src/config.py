import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# override=True forces reload even if vars are already set
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Audio Settings
TTS_VOICE = "en-US-ChristopherNeural" # High quality male voice
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

# Visual Settings
IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "standard"
