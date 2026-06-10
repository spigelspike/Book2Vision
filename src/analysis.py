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
                # Build visual anchors and infer scene-character mappings
                post_process_analysis(result)
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
                                post_process_analysis(result)
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
                post_process_analysis(result)
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
    
    # Entity format: [name, role, visual_description, outfit, signature_prop, visual_anchor]
    # Descriptions are blank for regex fallback — regex can't infer appearance
    top_entities = [
        [name, "Character", "", "", "none", f"{name}, a character in the story"]
        for name, count in counts.most_common(5)
    ]
    
    fallback_result = {
        "entities": top_entities,
        "keywords": [],
        "scenes": [
            {
                "description": "The story begins, introducing the main characters and setting.",
                "excerpt": "The beginning...",
                "narrator_intro": "Our story starts here.",
                "emotion": "anticipation",
                "mood": "introductory",
                "environment": "opening scene",
                "characters_in_scene": []
            },
            {
                "description": "A key event occurs that sets the plot in motion.",
                "excerpt": "Something happens...",
                "narrator_intro": "Then, everything changed.",
                "emotion": "surprise",
                "mood": "dynamic",
                "environment": "key location",
                "characters_in_scene": []
            },
            {
                "description": "The tension rises as the characters face a challenge.",
                "excerpt": "The conflict grows...",
                "narrator_intro": "The stakes were getting higher.",
                "emotion": "tension",
                "mood": "intense",
                "environment": "challenging setting",
                "characters_in_scene": []
            },
            {
                "description": "The story reaches its conclusion or a dramatic moment.",
                "excerpt": "The climax approaches...",
                "narrator_intro": "Finally, the moment of truth.",
                "emotion": "dramatic",
                "mood": "climactic",
                "environment": "final setting",
                "characters_in_scene": []
            }
        ]
    }
    post_process_analysis(fallback_result)
    return fallback_result

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
                "environment": "in the story setting",
                "characters_in_scene": []
            })
        analysis_result["scenes"] = scenes
    return analysis_result


def build_visual_anchors(entities: list) -> dict:
    """
    Builds compact, image-gen-optimized visual anchor strings per character.
    Prefers the 6th field (visual_anchor) extracted by the LLM if available,
    otherwise assembles one from fields 0-4.
    Returns: {character_name: anchor_string}
    """
    anchors = {}
    for entity in entities:
        if isinstance(entity, (list, tuple)):
            name = entity[0] if len(entity) > 0 else ""
            if not name:
                continue

            # Prefer the dedicated visual_anchor field (index 5) if present and non-trivial
            if len(entity) >= 6 and entity[5] and len(str(entity[5])) > 15:
                anchors[name] = str(entity[5])
            else:
                # Assemble from available fields
                physical = str(entity[2]) if len(entity) > 2 else ""
                outfit   = str(entity[3]) if len(entity) > 3 else ""
                prop     = str(entity[4]) if len(entity) > 4 else ""

                parts = [name]
                if physical:
                    parts.append(physical[:150])
                if outfit:
                    parts.append(f"wearing {outfit[:100]}")
                if prop and prop.lower() not in ["none", "n/a", ""]:
                    parts.append(f"holding {prop[:80]}")

                anchors[name] = ", ".join(parts)

        elif isinstance(entity, dict):
            name = entity.get("name", "")
            if not name:
                continue

            anchor = entity.get("visual_anchor", "")
            if anchor and len(anchor) > 15:
                anchors[name] = anchor
            else:
                physical = entity.get("visual_description", "")
                outfit   = entity.get("outfit", "")
                prop     = entity.get("signature_prop", "")

                parts = [name]
                if physical:
                    parts.append(physical[:150])
                if outfit:
                    parts.append(f"wearing {outfit[:100]}")
                if prop and prop.lower() not in ["none", "n/a", ""]:
                    parts.append(f"holding {prop[:80]}")

                anchors[name] = ", ".join(parts)

    return anchors


def post_process_analysis(analysis_result: dict) -> dict:
    """
    Post-processes the analysis result to:
    1. Build and store visual anchor strings per character (used by visuals.py).
    2. Warn about vague character descriptions that will hurt image accuracy.
    3. Infer `characters_in_scene` for any scenes the LLM left that field out of.
    """
    entities = analysis_result.get("entities", [])
    scenes   = analysis_result.get("scenes", [])

    # 1. Build and attach visual anchors
    visual_anchors = build_visual_anchors(entities)
    analysis_result["visual_anchors"] = visual_anchors
    print(f"  -> Built {len(visual_anchors)} visual anchors: {list(visual_anchors.keys())}")

    # 2. Validate description quality — warn on suspiciously short descriptions
    for entity in entities:
        if isinstance(entity, (list, tuple)) and len(entity) >= 3:
            name, physical = entity[0], str(entity[2])
            if len(physical) < 30:
                print(f"  ⚠ WARNING: '{name}' has a very vague physical description "
                      f"({len(physical)} chars: '{physical}'). Image accuracy will suffer.")

    # 3. Infer characters_in_scene for scenes that are missing it
    all_names = list(visual_anchors.keys())
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        if "characters_in_scene" not in scene:
            # Scan the scene description + excerpt for character names
            search_text = scene.get("description", "") + " " + scene.get("excerpt", "")
            mentioned = [name for name in all_names if name and name in search_text]
            scene["characters_in_scene"] = mentioned
            if mentioned:
                print(f"  -> Scene {i+1}: inferred characters_in_scene = {mentioned}")

    return analysis_result