import asyncio
import sys
from src.audio import generate_audio_pollinations

async def test_audio():
    print("Testing Pollinations TTS integration...")
    try:
        res = await generate_audio_pollinations("Hello world, this is a test of the Pollinations integration in Book 2 Vision.", "test_integration.mp3", voice_id="nova")
        print(f"Success! Saved to {res}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_audio())
