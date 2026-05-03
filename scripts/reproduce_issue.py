import asyncio
import os
import shutil
from src.visuals import generate_images

async def main():
    output_dir = "test_output_hybrid"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    semantic_map = {
        "scenes": [
            {"description": "A cyberpunk street market at night with neon lights."}
        ],
        "entities": [
            ("Cyborg", "Merchant", "Half-human half-machine with a glowing eye")
        ]
    }

    print("Testing Hybrid Generation (Pollinations for Scene, DepAI for Entity)...")
    try:
        # Note: This requires API keys to be set in .env
        images = await generate_images(
            semantic_map, 
            output_dir, 
            style="cyberpunk", 
            title="Hybrid Test", 
            scene_provider="pollinations",
            entity_provider="deapi"
        )
        print(f"Generated Images: {images}")
    except Exception as e:
        print(f"Hybrid Generation Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
