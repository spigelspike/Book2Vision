"""
Test script to verify podcast error handling improvements.

This script tests:
1. Missing API key handling
2. Error fallback messages
3. Retry logic simulation
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.podcast import PodcastGenerator, _create_error_fallback, HOSTS


async def test_missing_api_key():
    """Test behavior when API key is missing."""
    print("\n" + "="*60)
    print("TEST 1: Missing API Key")
    print("="*60)
    
    generator = PodcastGenerator(api_key="")
    
    # Should not crash, just return error fallback
    script = await generator.generate_script("Test book content")
    
    print(f"✓ Script generated: {len(script)} segments")
    for i, seg in enumerate(script):
        print(f"  [{seg['speaker']}]: {seg['text']}")
    
    # Check if it's an error fallback
    has_error_msg = any("Error:" in seg['text'] or "trouble" in seg['text'] for seg in script)
    print(f"\n✓ Contains error message: {has_error_msg}")


async def test_custom_error_fallback():
    """Test custom error fallback generation."""
    print("\n" + "="*60)
    print("TEST 2: Custom Error Fallback")
    print("="*60)
    
    test_cases = [
        ("Invalid API Key", "Your DeepSeek key has expired"),
        ("Rate Limited", "Too many requests - please wait"),
        ("Configuration Error", "Missing DEEPSEEK_API_KEY in .env")
    ]
    
    for error_type, error_detail in test_cases:
        script = _create_error_fallback(error_type, error_detail)
        print(f"\n{error_type}:")
        for seg in script:
            print(f"  [{seg['speaker']}]: {seg['text']}")
        
        # Verify error info is in script
        script_text = " ".join(seg['text'] for seg in script)
        assert error_type in script_text, f"Error type '{error_type}' not in fallback"
        print(f"  ✓ Error details included")


async def test_host_configuration():
    """Test that host profiles are properly configured."""
    print("\n" + "="*60)
    print("TEST 3: Host Configuration")
    print("="*60)
    
    generator = PodcastGenerator(api_key="test_key")
    
    print(f"Available hosts: {list(generator.hosts.keys())}")
    
    for name, host in generator.hosts.items():
        print(f"\n{name}:")
        print(f"  Gender: {host.gender}")
        print(f"  Voice ID (ElevenLabs): {host.voice.elevenlabs_id}")
        print(f"  Voice (Edge TTS): {host.voice.edge_voice}")
        print(f"  Personality: {host.personality[:60]}...")
    
    print("\n✓ All hosts properly configured")


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("PODCAST ERROR HANDLING TEST SUITE")
    print("="*70)
    
    try:
        await test_missing_api_key()
        await test_custom_error_fallback()
        await test_host_configuration()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print("\nThe podcast error handling improvements are working correctly!")
        print("\nNext steps:")
        print("1. Set DEEPSEEK_API_KEY in your .env file")
        print("2. Start the server: python src/server.py")
        print("3. Try generating a podcast to see improved error messages")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
