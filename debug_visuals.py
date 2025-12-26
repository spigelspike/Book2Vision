import os
import sys
import logging
from src.visuals import generate_images

# Setup logging
logging.basicConfig(level=logging.INFO)

def debug_visuals():
    print("=== Debugging Visuals Generation ===")
    
    output_dir = "temp_upload/visuals_debug"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Mock semantic map similar to what might be produced
    semantic_map = {
        "scenes": [
            "A dense jungle with tall ancient trees and sunlight filtering through leaves.",
            "A T-Rex roaring in a clearing, showing its massive teeth.",
            "Captain Nova standing bravely with a futuristic gadget in hand.",
            "The team escaping in a high-tech vehicle as the dinosaur chases them."
        ],
        "entities": [
            ("Captain Nova", "Protagonist", "A brave space explorer"),
            ("T-Rex", "Antagonist", "A massive carnivorous dinosaur"),
            ("Velociraptors", "Minions", "Fast and cunning pack hunters")
        ]
    }
    
    title = "Dino F35 Story.pdf"
    
    print(f"Output Directory: {output_dir}")
    print("Starting generation...")
    
    try:
        import asyncio
        images = asyncio.run(generate_images(semantic_map, output_dir, style="storybook", seed=42, title=title))
        print(f"✅ Generated {len(images)} images.")
        for img in images:
            print(f" - {os.path.basename(img)}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")

if __name__ == "__main__":
    debug_visuals()
