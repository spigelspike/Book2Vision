import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis import semantic_analysis

async def test_no_summary():
    print("Testing semantic_analysis (Regex Fallback)...")
    
    # Unset API key to force regex fallback
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
        
    text = "This is a test story. Once upon a time, there was a character named Alice. She was a protagonist."
    result = await semantic_analysis(text)
    
    if "summary" in result:
        print("❌ FAILURE: 'summary' field found in result.")
        print(f"Result keys: {result.keys()}")
    else:
        print("✅ SUCCESS: 'summary' field NOT found in result.")
        print(f"Result keys: {result.keys()}")

if __name__ == "__main__":
    asyncio.run(test_no_summary())
