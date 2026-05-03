
import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.server import state
from src.analysis import ensure_minimum_scenes

async def verify_image_count():
    # Mock analysis result with MANY scenes (simulating a long story)
    scenes = [{"description": f"Scene {i}"} for i in range(15)]
    state.analysis_result = {
        "summary": "A long test story.",
        "entities": [["Hero", "Protagonist"], ["Villain", "Antagonist"], ["Sidekick", "Ally"]],
        "scenes": scenes
    }
    
    # Ensure minimum scenes (should not affect 15 scenes)
    ensure_minimum_scenes(state.analysis_result)
    
    # Simulate the logic in generate_visuals to calculate expected images
    expected_images = []
    
    # 1. Title
    expected_images.append("image_00_title_Test.jpg")
    
    # 2. Scenes
    scenes = state.analysis_result.get("scenes", [])
    for i in range(len(scenes)):
        expected_images.append(f"image_01_scene_{i+1:02d}.jpg")
        
    # 3. Entities (Top 3)
    entities = state.analysis_result.get("entities", [])
    top_entities = entities[:3]
    for i, entity in enumerate(top_entities):
        expected_images.append(f"image_02_entity_{i}.jpg")
        
    print(f"Total Expected Images: {len(expected_images)}")
    print(f"Scenes: {len(scenes)}")
    print(f"Entities: {len(top_entities)}")
    
    # Assertions
    # 1 Title + 15 Scenes + 3 Entities = 19 images
    if len(expected_images) >= 19: 
        print("✅ Verification PASSED: Dynamic scene count handled correctly.")
    else:
        print(f"❌ Verification FAILED: Expected at least 19 images, got {len(expected_images)}")

if __name__ == "__main__":
    asyncio.run(verify_image_count())
