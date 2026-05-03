
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.getcwd())

# Mock the database and other dependencies before importing server
sys.modules['src.library'] = MagicMock()
sys.modules['src.ingestion'] = MagicMock()
sys.modules['src.analysis'] = MagicMock()
sys.modules['src.audio'] = MagicMock()
sys.modules['src.knowledge'] = MagicMock()
sys.modules['src.podcast'] = MagicMock()
sys.modules['src.video'] = MagicMock()
sys.modules['src.storybook'] = MagicMock()

# Import the function we want to test (we need to patch the imports inside server.py)
# Since server.py has top-level code that runs on import, we might need to be careful.
# Instead, let's just inspect the file content to verify the sequence, 
# or run a mock test if possible. 
# Given the complexity of mocking FastAPI app state, a static analysis or simple mock of the function is better.

def verify_sequence():
    with open("src/server.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if generate_entity_image appears before generate_poster_with_deapi in the background task
    entity_gen_index = content.find("await generate_entity_image")
    cover_gen_index = content.find("await generate_poster_with_deapi")
    
    print(f"Entity Generation Index: {entity_gen_index}")
    print(f"Cover Generation Index: {cover_gen_index}")
    
    if entity_gen_index != -1 and cover_gen_index != -1 and entity_gen_index < cover_gen_index:
        print("✅ Verification PASSED: Entity generation is sequenced BEFORE cover generation.")
    else:
        print("❌ Verification FAILED: Sequence is incorrect or calls are missing.")

    # Check visuals.py for provider
    with open("src/visuals.py", "r", encoding="utf-8") as f:
        visuals_content = f.read()
    
    if 'entity_provider = "pollinations"' in visuals_content:
        print("✅ Verification PASSED: Entity provider set to 'pollinations'.")
    else:
        print("❌ Verification FAILED: Entity provider NOT set to 'pollinations'.")

if __name__ == "__main__":
    verify_sequence()
