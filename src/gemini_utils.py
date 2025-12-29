import google.generativeai as genai
import os
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model cache to avoid repeated API calls
_model_cache = {"models": None, "timestamp": 0}
CACHE_TTL = 3600  # Cache for 1 hour

def get_gemini_model(capability="text", api_key=None):
    """
    Returns a valid GenerativeModel instance based on capability and availability.
    
    Args:
        capability (str): "text", "vision", or "flash" (fast).
        api_key (str): Optional API key. If not provided, looks in env.
        
    Returns:
        genai.GenerativeModel: A configured model instance.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        
    if not api_key:
        logger.error("GEMINI_API_KEY not found.")
        raise ValueError("GEMINI_API_KEY not found.")

    genai.configure(api_key=api_key)
    
    # Preferred models by capability (Updated with older models for fallback)
    preferences = {
        "text": ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-flash-latest", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.0-pro"],
        "vision": ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-flash-latest", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-pro-vision"],
        "flash": ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-flash-latest", "gemini-2.0-flash-exp", "gemini-1.5-flash-8b", "gemini-1.0-pro"]
    }
    
    preferred_list = preferences.get(capability, preferences["text"])
    
    # Check cache first
    current_time = time.time()
    if _model_cache["models"] is None or (current_time - _model_cache["timestamp"]) > CACHE_TTL:
        # Cache miss or expired - refresh
        available_models = []
        try:
            print("--- Checking Available Gemini Models (caching) ---")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    clean_name = m.name.replace("models/", "")
                    available_models.append(clean_name)
                    print(f"Found supported model: {clean_name}")
            print("----------------------------------------")
            _model_cache["models"] = available_models
            _model_cache["timestamp"] = current_time
        except Exception as e:
            logger.warning(f"Could not list models (API key: {api_key[:10] if api_key else 'None'}...): {e}. Using defaults.")
            print(f"Error listing models: {e}")
            # If cache exists, use stale data
            if _model_cache["models"] is not None:
                available_models = _model_cache["models"]
            else:
                available_models = []
    else:
        # Cache hit
        available_models = _model_cache["models"]
        print(f"Using cached model list ({len(available_models)} models)")

    # Find first match
    selected_model_name = None
    
    if available_models:
        # Intersect preferred with available
        for pref in preferred_list:
            if pref in available_models:
                selected_model_name = pref
                break
    
    # If no match found or listing failed, default to the first preferred
    if not selected_model_name:
        if available_models:
             # If we have a list but none of our prefs matched, pick the first available one!
            selected_model_name = available_models[0]
            logger.warning(f"No preferred model found. Defaulting to first available: {selected_model_name}")
        else:
            # Total failure to list, just guess
            selected_model_name = preferred_list[0]
            logger.warning(f"Model listing failed. Defaulting to: {selected_model_name}")
    else:
        logger.info(f"Selected Gemini model: {selected_model_name}")

    return genai.GenerativeModel(selected_model_name)
