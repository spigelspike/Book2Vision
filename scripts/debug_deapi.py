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

from src.visuals import generate_poster_with_deapi

async def test_deapi():
    print("\n--- Testing deAPI ---")
    api_key = os.getenv("DEAPI_API_KEY")
    if not api_key:
        print("❌ DEAPI_API_KEY not found in environment.")
        return

    print(f"✅ DEAPI_API_KEY found: {api_key[:5]}...")

    try:
        output_dir = "debug_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Generating poster with deAPI...")
        poster = await generate_poster_with_deapi("Debug Title", "Debug Author", output_dir)
        
        if poster:
            print(f"✅ Poster generated: {poster}")
        else:
            print("❌ Poster generation returned None.")
            
    except Exception as e:
        print(f"❌ deAPI failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deapi())
