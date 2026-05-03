
import asyncio
import os
import sys
import shutil

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import config
from src.visuals import generate_images

async def test_generation():
    output_dir = "debug_output_images"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Mock semantic map with 4 scenes and 3 entities
    semantic_map = {
        "summary": "A test story about a cat.",
        "scenes": [
            {"description": "Scene 1: The cat wakes up.", "emotion": "sleepy", "mood": "calm", "environment": "bedroom"},
            {"description": "Scene 2: The cat eats breakfast.", "emotion": "happy", "mood": "bright", "environment": "kitchen"},
            {"description": "Scene 3: The cat chases a mouse.", "emotion": "excited", "mood": "tense", "environment": "garden"},
            {"description": "Scene 4: The cat sleeps again.", "emotion": "content", "mood": "peaceful", "environment": "sofa"}
        ],
        "entities": [
            ["Whiskers", "Protagonist", "A fluffy orange tabby cat"],
            ["Squeaky", "Antagonist", "A small grey mouse"],
            ["Owner", "Support", "A kind human"]
        ]
    }

    print("Starting generation test...")
    images = await generate_images(semantic_map, output_dir, style="cartoon", title="The Lazy Cat")
    
    print(f"Generated {len(images)} images.")
    for img in images:
        print(f" - {os.path.basename(img)}")

if __name__ == "__main__":
    asyncio.run(test_generation())
