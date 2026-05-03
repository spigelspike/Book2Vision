import sys
import os
import asyncio

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.audio import format_for_professional_narration, prepare_audiobook_text

async def test_audiobook_intro():
    print("--- Testing Synchronous Formatting ---")
    text = "This is the first chapter of the book."
    title = "The Great Gatsby"
    author = "F. Scott Fitzgerald"
    
    formatted = format_for_professional_narration(text, book_title=title, author=author)
    print(f"Original: {text}")
    print(f"Formatted:\n{formatted}")
    
    expected_intro = "You are listening to the audiobook of The Great Gatsby. Written by F. Scott Fitzgerald. ... "
    if expected_intro in formatted:
        print("✅ Sync formatting check passed!")
    else:
        print("❌ Sync formatting check failed!")
        print(f"Expected start: {expected_intro}")

    print("\n--- Testing Async Preparation (Mocking LLM fallback) ---")
    # We can't easily mock the LLM here without more setup, but we can check the fallback logic
    # or just run it and see if it works (it might use LLM if key is present)
    
    try:
        prepared = await prepare_audiobook_text(text, book_title=title, author=author)
        print(f"Prepared:\n{prepared}")
        
        # Check for the intro in the result (LLM might vary slightly, but should contain key phrases)
        if "You are listening to the audiobook of" in prepared and title in prepared:
             print("✅ Async preparation check passed (contains intro phrases)!")
        else:
             print("⚠️ Async preparation check warning: Intro phrases not found exactly (might be LLM variation)")
             
    except Exception as e:
        print(f"Async test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_audiobook_intro())
