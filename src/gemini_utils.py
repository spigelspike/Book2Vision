try:
    from google import genai
except ImportError:
    print("  -> ERROR: New 'google-genai' SDK not found. Please run: pip install google-genai")
    genai = None

import os
import logging
import time
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model cache to avoid repeated API calls (keyed by API key prefix)
_model_cache = {} # { key_prefix: {"models": [], "timestamp": 0} }
_key_cooldowns = {} # { key_prefix: timestamp_when_usable }
CACHE_TTL = 3600  # Cache for 1 hour
COOLDOWN_TIME = 300 # 5 minutes cooldown on 429 errors

# Global pacing state
_key_semaphores = {} # { key_prefix: asyncio.Semaphore }

# Global next available time to prevent burning through all keys during a 429
_global_cooldown_until = 0

async def gemini_generate_content_pacing(client, model_name, contents, api_key, config=None):
    """
    Wraps the Gemini call with a per-key semaphore and a small pacing delay.
    Now respects global cooldowns and specific retryDelay from 429 errors.
    """
    global _global_cooldown_until
    prefix = api_key[:15] if api_key else "default"
    
    # Initialize semaphore for this key if it doesn't exist
    if prefix not in _key_semaphores:
        _key_semaphores[prefix] = asyncio.Semaphore(1)
        
    async with _key_semaphores[prefix]:
        # Check global cooldown first
        now = time.time()
        if now < _global_cooldown_until:
            wait_remaining = _global_cooldown_until - now
            print(f"  -> Gemini is on global cooldown. Waiting {wait_remaining:.1f}s...")
            await asyncio.sleep(wait_remaining)
            
        # Small artificial delay for the specific key
        await asyncio.sleep(0.5) 
        
        try:
            # Execute the blocking call in a thread
            if config:
                response = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=contents, config=config)
            else:
                response = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=contents)
        except Exception as e:
            error_str = str(e)
            
            # 429 / RESOURCE_EXHAUSTED / 503 UNAVAILABLE Handling
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str or "UNAVAILABLE" in error_str:
                # Extract wait time if available (e.g., "Please retry in 15.514s")
                import re
                wait_match = re.search(r"retry in ([\d\.]+)s", error_str)
                actual_wait = float(wait_match.group(1)) if wait_match else 3.0 # Default
                
                # Cap the maximum wait time so the user doesn't wait forever, max 3 seconds wait
                wait_time = min(actual_wait, 3.0)
                
                # Set global cooldown so other keys don't burn
                _global_cooldown_until = time.time() + wait_time + 1.0
                
                print(f"  -> Gemini rate limited/unavailable. Waiting {wait_time}s. Pausing all Gemini keys...")
                await asyncio.sleep(wait_time + 0.5) 
                
                # If blocked or rate limited, try forcing 3.1-flash-lite immediately after the wait
                if "gemini-3.5-flash" in model_name or "gemini-flash-latest" in model_name or "2.0" in model_name:
                    print(f"  -> Retrying with gemini-3.1-flash-lite...")
                    try:
                        fallback_model = "gemini-3.1-flash-lite"
                        if config:
                            response = await asyncio.to_thread(client.models.generate_content, model=fallback_model, contents=contents, config=config)
                        else:
                            response = await asyncio.to_thread(client.models.generate_content, model=fallback_model, contents=contents)
                        return response
                    except Exception as e2:
                        raise e2
                else:
                    raise e
            else:
                raise e
            
        # Post-request delay for the specific key to "breathe"
        await asyncio.sleep(1.0)
        return response

def mark_key_failed(api_key):
    """Marks a key as being on cooldown due to rate limits."""
    if not api_key: return
    prefix = api_key[:15]
    _key_cooldowns[prefix] = time.time() + COOLDOWN_TIME
    logger.warning(f"[WAIT] Gemini Key {prefix}... marked as FAILED. Cooldown for 5 mins.")

def is_key_on_cooldown(api_key):
    """Checks if a key is currently on cooldown."""
    if not api_key: return False
    prefix = api_key[:15]
    cooldown_until = _key_cooldowns.get(prefix, 0)
    if time.time() < cooldown_until:
        return True
    return False

# Global cache for clients to avoid re-initializing them repeatedly
_client_cache = {} # { api_key: genai.Client }

def get_gemini_model(capability="text", api_key=None):
    """
    Returns a configured Gemini client and the best available model name.
    Reuses clients to prevent connection-based rate limiting.
    Based on your original working reference.
    """
    if genai is None:
        print("  -> CRITICAL: Google GenAI SDK is not available.")
        return None, None
        
    if not api_key:
        from src.config import GEMINI_API_KEY
        api_key = GEMINI_API_KEY
        
    if not api_key:
        return None, None
        
    prefix = api_key[:15]
    
    # Reuse client if available
    if api_key in _client_cache:
        client = _client_cache[api_key]
    else:
        try:
            client = genai.Client(api_key=api_key)
            _client_cache[api_key] = client
        except Exception as e:
            print(f"  -> Error initializing client: {e}")
            return None, None
    
    # Discovery with safety
    now = time.time()
    models = []
    try:
        # Check cache
        cached = _model_cache.get(prefix)
        if cached and (now - cached["timestamp"] < CACHE_TTL):
            models = cached["models"]
        else:
            print(f"--- Discovering Models for key {prefix}... ---")
            for m in client.models.list():
                clean_name = m.name.replace("models/", "")
                models.append(clean_name)
            
            _model_cache[prefix] = {"models": models, "timestamp": now}
            print(f"  -> Detected Models: {models}")
            
    except Exception as e:
        print(f"  -> Model Discovery Warning: {e}. Using defaults.")
        models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
    
    # Selection Strategy based on your reference preferences
    preferences = {
        "text": ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-lite-latest"],
        "vision": ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-lite-latest"],
        "flash": ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-lite-latest"]
    }
    
    preferred_list = preferences.get(capability, preferences["text"])
    
    selected_model = None
    if models:
        for pref in preferred_list:
            if pref in models:
                selected_model = pref
                break
                
    if not selected_model:
        selected_model = models[0] if models else preferred_list[0]
        
    return client, selected_model

