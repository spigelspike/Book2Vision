import os
import sys
import asyncio
import shutil

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.visuals import generate_images, generate_entity_image
from src.audio import generate_audio

async def test_audio():
    print("\n=== Testing Audio Generation ===")
    text = "This is a test of the audio generation system."
    output_path = "test_audio.mp3"
    
    # Test Inbuilt (Edge TTS)
    print("\n-- Testing Inbuilt (Edge TTS) --")
    try:
        await generate_audio(text, output_path, provider="inbuilt")
        print("✅ Inbuilt Audio Success")
    except Exception as e:
        print(f"❌ Inbuilt Audio Failed: {e}")

    # Test ElevenLabs (if key exists, otherwise it should fallback or fail gracefully)
    print("\n-- Testing ElevenLabs --")
    try:
        await generate_audio(text, "test_eleven.mp3", provider="elevenlabs")
        print("✅ ElevenLabs Audio Success (or fallback)")
    except Exception as e:
        print(f"❌ ElevenLabs Audio Failed: {e}")

async def test_visuals():
    print("\n=== Testing Visuals Generation ===")
    output_dir = "test_visuals"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # Mock semantic map
    semantic_map = {
        "scenes": ["A beautiful sunny day in a magical forest."],
        "entities": [("Alice", "Protagonist", "A young girl with blue dress")]
    }
    
    print("\n-- Testing Scene Generation --")
    try:
        images = generate_images(semantic_map, output_dir, style="storybook")
        print(f"✅ Generated {len(images)} images")
    except Exception as e:
        print(f"❌ Visuals Generation Failed: {e}")

    print("\n-- Testing Entity Image Generation --")
    try:
        img = generate_entity_image("Alice", "Protagonist", output_dir)
        if img:
            print(f"✅ Entity Image Success: {img}")
        else:
            print("❌ Entity Image Returned None")
    except Exception as e:
        print(f"❌ Entity Image Exception: {e}")

async def main():
    await test_audio()
    await test_visuals()

if __name__ == "__main__":
    asyncio.run(main())
