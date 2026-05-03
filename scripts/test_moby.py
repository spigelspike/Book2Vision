
import asyncio
import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.analysis import semantic_analysis

MOBY_DICK_TEXT = """
Moby-Dick is the tale of Captain Ahab, a man consumed by obsession.

After losing his leg to a massive white whale known as Moby Dick, Ahab commands the whaling ship Pequod with one goal: revenge. The crew, including the thoughtful sailor Ishmael, senses danger but follows their captain across endless oceans.

Moby Dick is not just a whale—he represents nature’s raw power and mystery. As the hunt drags on, Ahab’s obsession grows stronger, blinding him to reason and warning.

In a final, violent encounter, the whale destroys the Pequod. Ahab perishes with his obsession, while Ishmael alone survives to tell the story.

Moby-Dick is a powerful reminder of how obsession can destroy a person—and how nature will always remain beyond human control.
"""

async def test_extraction():
    print("Analyzing Moby Dick text...")
    result = await semantic_analysis(MOBY_DICK_TEXT)
    
    print("\n--- Extracted Entities ---")
    for entity in result.get("entities", []):
        print(entity)

if __name__ == "__main__":
    asyncio.run(test_extraction())
