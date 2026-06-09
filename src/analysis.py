from collections import Counter
import json
import os
import re
import asyncio
from google import genai
from src.config import GEMINI_API_KEYS, PODCAST_API_KEYS, OPENROUTER_API_KEY
from src.gemini_utils import get_gemini_model

# Compile regex pattern once for performance
CAPITALIZED_PATTERN = re.compile(r'\b[A-Z][a-z]+\b')

async def semantic_analysis(text):
    """
    Performs semantic analysis to extract entities and key concepts (Async).
    Priority: Gemini -> Basic Regex
    """
    # 1. Try Gemini with Key Rotation (Allocated for Analysis)
    from src.config import get_allocated_keys
    available_keys = get_allocated_keys(purpose="analysis")
    
    if available_keys:
        from src.gemini_utils import is_key_on_cooldown, mark_key_failed
    
    for i, key in enumerate(available_keys):
        # SKIP if key is on cooldown
        if is_key_on_cooldown(key):
            print(f"  -> Skipping Gemini Key {i+1} (on cooldown due to 429)")
            continue
            
        try:
            print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for Analysis...")
            result = await semantic_analysis_with_llm(text, key)
            
            # If successful and has entities, return it
            if result and result.get("entities"):
                # Enforce minimum scenes
                ensure_minimum_scenes(result)
                print(f"SUCCESS: Gemini analysis succeeded using key {i+1}. Found {len(result.get('entities', []))} entities.")
                return result
                
            print(f"WARNING: Key {i+1} returned empty analysis. Trying next...")
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # 🛡️ SMART RETRY: Check if it's a transient RPM limit (12s wait)
                # [SMART RETRY]: Check if it's a transient RPM limit (12s wait)
                import re
                retry_match = re.search(r"retryDelay': '(\d+)s'", error_str)
                if retry_match:
                    delay = int(retry_match.group(1))
                    if delay > 3:
                        print(f"  -> [RPM LIMIT]: RPM Limit reached. Skipping long wait ({delay}s) and falling back immediately...")
                    else:
                        print(f"  -> [RPM LIMIT]: RPM Limit reached. Waiting {delay+1}s for smart retry...")
                        await asyncio.sleep(delay + 1)
                        try:
                            print(f"  -> INFO: Retrying Gemini Key {i+1}...")
                            result = await semantic_analysis_with_llm(text, key)
                            if result and result.get("entities"):
                                ensure_minimum_scenes(result)
                                return result
                        except: pass # If retry fails, move to circuit breaker
                
                mark_key_failed(key)
            print(f"WARNING: Key {i+1} failed with error: {e}")
            continue
    
    # 2. NEW: FALLBACK TO DEEPSEEK (OPENROUTER) IF GEMINI FAILS
    from src.config import OPENROUTER_API_KEY
    if OPENROUTER_API_KEY:
        try:
            print("--- Falling back to DeepSeek (OpenRouter) for Analysis ---")
            result = await semantic_analysis_with_deepseek(text, OPENROUTER_API_KEY)
            if result and result.get("entities"):
                ensure_minimum_scenes(result)
                return result
        except Exception as e:
            print(f"  -> DeepSeek analysis failed: {e}")

    # 3. Basic Regex Fallback
    print("Falling back to Basic Regex Analysis...")
    
    # Limit scan to first 10K characters for performance
    scan_text = text[:10000]
    words = CAPITALIZED_PATTERN.findall(scan_text)
    
    common_stops = {
        "The", "A", "An", "It", "He", "She", "They", "But", "And", "When", "Then", "Suddenly",
        "Meanwhile", "However", "Although", "Okay", "So", "If", "This", "That", "There", "Here",
        "What", "Why", "How", "Who", "Where", "Beneath", "Above", "Behind", "Inside", "Outside",
        "Near", "Far", "Just", "Only", "Very", "Really", "Now", "Later", "Soon", "Yesterday",
        "Today", "Tomorrow", "Yes", "No", "Please", "Thank", "Thanks", "Hello", "Hi", "Goodbye",
        "Mr", "Mrs", "Ms", "Dr", "Prof", "Captain", "Sergeant", "General", "King", "Queen",
        "Prince", "Princess", "Lord", "Lady", "Sir", "Madam", "One", "Two", "Three", "First",
        "Second", "Third", "Next", "Last", "Finally", "Also", "Besides", "Moreover", "Furthermore",
        "In", "On", "At", "To", "For", "With", "By", "From", "Of", "About", "As", "Like"
    }
    
    candidates = [w for w in words if w not in common_stops and len(w) > 2]
    
    # Count frequency
    counts = Counter(candidates)
    
    # Entity format: [name, role, visual_description]
    # Empty description for fallback since regex can't infer appearance
    top_entities = [
        [name, "Character", ""]  # description blank - not available from regex
        for name, count in counts.most_common(5)
    ]
    
    return {
        "entities": top_entities,
        "keywords": [],
        "scenes": [
            {
                "description": "The story begins, introducing the main characters and setting.",
                "excerpt": "The beginning...",
                "narrator_intro": "Our story starts here.",
                "emotion": "anticipation",
                "mood": "introductory",
                "environment": "opening scene"
            },
            {
                "description": "A key event occurs that sets the plot in motion.",
                "excerpt": "Something happens...",
                "narrator_intro": "Then, everything changed.",
                "emotion": "surprise",
                "mood": "dynamic",
                "environment": "key location"
            },
            {
                "description": "The tension rises as the characters face a challenge.",
                "excerpt": "The conflict grows...",
                "narrator_intro": "The stakes were getting higher.",
                "emotion": "tension",
                "mood": "intense",
                "environment": "challenging setting"
            },
            {
                "description": "The story reaches its conclusion or a dramatic moment.",
                "excerpt": "The climax approaches...",
                "narrator_intro": "Finally, the moment of truth.",
                "emotion": "dramatic",
                "mood": "climactic",
                "environment": "final setting"
            }
        ]
    }

from src.prompts import SEMANTIC_ANALYSIS_PROMPT

async def semantic_analysis_with_llm(text, api_key):
    print("Using Gemini for Semantic Analysis...")
    
    client, model_name = get_gemini_model(capability="text", api_key=api_key)
    
    prompt = SEMANTIC_ANALYSIS_PROMPT.format(text=text[:100000])
    
    from src.gemini_utils import gemini_generate_content_pacing
    response = await gemini_generate_content_pacing(
        client, 
        model_name, 
        contents=prompt,
        api_key=api_key
    )
    
    if not response or not hasattr(response, 'text'):
        return {"entities": [], "keywords": []}
        
    response_text = response.text.strip()
    print(f"Gemini Analysis Response: {response_text[:200]}...")  # Log first 200 chars
    
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
        
    return json.loads(response_text)

async def semantic_analysis_with_deepseek(text, api_key):
    """Fallback analysis using DeepSeek via OpenRouter."""
    from openai import AsyncOpenAI
    from src.prompts import SEMANTIC_ANALYSIS_PROMPT
    
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    try:
        response = await client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=[
                {"role": "system", "content": "You are a literary analyst. Return valid JSON."},
                {"role": "user", "content": SEMANTIC_ANALYSIS_PROMPT.format(text=text[:15000])}
            ],
            response_format={"type": "json_object"}
        )
        if response and response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            if content:
                # Remove potential markdown
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                try:
                    return json.loads(content)
                except Exception as je:
                    print(f"Error parsing DeepSeek JSON: {je}")
            
        print("DeepSeek returned empty or invalid response.")
        return None
    except Exception as e:
        print(f"DeepSeek Analysis Exception: {e}")
        return None

def chapter_segmentation(text):
    """
    Segments text into chapters based on headings.
    Simple heuristic: Look for "Chapter" or all-caps lines.
    """
    chapters = []
    lines = text.split('\n')
    current_chapter = {"title": "Introduction", "content": ""}
    
    for line in lines:
        if line.strip().lower().startswith("chapter") or (line.isupper() and len(line.strip()) < 50):
            if current_chapter["content"].strip():
                chapters.append(current_chapter)
            current_chapter = {"title": line.strip(), "content": ""}
        else:
            current_chapter["content"] += line + "\n"
            
    if current_chapter["content"].strip():
        chapters.append(current_chapter)
        
    return chapters

def identify_visual_content(text):
    """
    Identifies segments that are good for visualization.
    """
    # Placeholder: look for descriptive words
    visual_keywords = ["see", "look", "diagram", "figure", "image", "picture", "scene"]
    # This is a very basic heuristic
    return []

def ensure_minimum_scenes(analysis_result, min_scenes=4):
    """
    Ensures the analysis result has at least min_scenes.
    Pads with generic scenes if necessary.
    Modifies the dictionary in-place.
    """
    scenes = analysis_result.get("scenes", [])
    if len(scenes) < min_scenes:
        print(f"WARNING: Only {len(scenes)} scenes found. Padding to {min_scenes} with generic scenes.")
        defaults = [
            "The journey continues as the plot unfolds.",
            "A moment of quiet reflection or building tension.",
            "The characters face a new challenge or revelation.",
            "The story reaches a pivotal turning point.",
            "New developments change the course of events.",
            "The atmosphere shifts as the story progresses."
        ]
        
        # Add defaults until we have min_scenes
        needed = min_scenes - len(scenes)
        for i in range(needed):
            scenes.append({
                "description": defaults[i % len(defaults)],
                "excerpt": "The story continues...",
                "narrator_intro": "Moving forward...",
                "emotion": "neutral",
                "mood": "atmospheric",
                "environment": "in the story setting"
            })
        analysis_result["scenes"] = scenes
    return analysis_result
