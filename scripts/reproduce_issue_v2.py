
import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis import semantic_analysis

async def test_analysis():
    text = "This is a short story. It has a beginning, a middle, and an end. The hero fights the villain. The end."
    print("Running analysis...")
    result = await semantic_analysis(text)
    print(f"Scenes found: {len(result.get('scenes', []))}")
    print(f"Entities found: {len(result.get('entities', []))}")
    print("Scenes:")
    for i, scene in enumerate(result.get('scenes', [])):
        print(f"  {i+1}. {scene.get('description', '')[:50]}...")

if __name__ == "__main__":
    asyncio.run(test_analysis())
