import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Load env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from src.visuals import generate_images, generate_poster_with_deapi
from src.prompts import TITLE_PROMPT_TEMPLATE

async def test_pollinations():
    print("\n--- Testing Pollinations ---")
    try:
        output_dir = "debug_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Mock semantic map
        semantic_map = {
            "scenes": ["A beautiful sunset over a calm ocean."],
            "entities": [["Hero", "Protagonist", "A brave warrior"]]
        }
        
        print("Generating images with Pollinations...")
        images = await generate_images(semantic_map, output_dir, title="Debug Book")
        print(f"Generated {len(images)} images.")
        for img in images:
            print(f" - {img}")
            
    except Exception as e:
        print(f"Pollinations failed: {e}")
        import traceback
        traceback.print_exc()

async def test_deapi():
    print("\n--- Testing deAPI ---")
    api_key = os.getenv("DEAPI_API_KEY")
    if not api_key:
        print("Skipping deAPI test: DEAPI_API_KEY not found.")
        return

    try:
        output_dir = "debug_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Generating poster with deAPI (Key: {api_key[:5]}...)...")
        poster = await generate_poster_with_deapi("Debug Title", "Debug Author", output_dir)
        
        if poster:
            print(f"Poster generated: {poster}")
        else:
            print("Poster generation returned None.")
            
    except Exception as e:
        print(f"deAPI failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_pollinations()
    await test_deapi()

if __name__ == "__main__":
    asyncio.run(main())
