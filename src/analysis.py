
from collections import Counter
import json
import os
import re
import google.generativeai as genai
from src.config import GEMINI_API_KEY
from src.gemini_utils import get_gemini_model

<<<<<<< HEAD
=======
# Compile regex pattern once for performance
CAPITALIZED_PATTERN = re.compile(r'\b[A-Z][a-z]+\b')

>>>>>>> temp_fix
def semantic_analysis(text):
    """
    Performs semantic analysis to extract entities and key concepts.
    Priority: Gemini -> Basic Regex
    """
    # 1. Try Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"=== SEMANTIC ANALYSIS DEBUG ===")
    print(f"API Key present: {bool(api_key)}")
    if api_key:
        result = semantic_analysis_with_llm(text, api_key)
        # If successful and has entities, return it
        if result and result.get("summary") != "Analysis failed." and result.get("entities"):
            print(f"✅ Gemini analysis succeeded. Found {len(result.get('entities', []))} entities.")
            return result
        print(f"❌ Gemini analysis failed or returned no entities. Result: {result}")
        print("Falling back...")


    # 3. Basic Regex Fallback
    print("Falling back to Basic Regex Analysis...")
<<<<<<< HEAD
    import re
    # Find capitalized words that might be names (simple heuristic)
    words = re.findall(r'\b[A-Z][a-z]+\b', text)
    
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
    top_entities = [[name, "Character", ""] for name, count in counts.most_common(5)]
=======
    
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
>>>>>>> temp_fix
    
    return {
        "summary": text[:200] + "...",
        "entities": top_entities,
        "keywords": [],
        "scenes": ["Scene 1: A key moment from the story."]
    }

def semantic_analysis_with_llm(text, api_key):
    print("Using Gemini for Semantic Analysis...")
    
    try:
        model = get_gemini_model(capability="text", api_key=api_key)
        
        prompt = f"""
        You are an expert literary analyst and visual storytelling assistant.

        Your task is to analyze the following book text and produce a CLEAN, VALID JSON OBJECT.
        Follow these rules very carefully:

        1. SUMMARY
           - Write a concise plot summary in natural language.
           - Maximum 3 sentences.
           - No bullet points.

        2. ENTITIES (CHARACTERS)
           - Identify the main characters only (3–10 characters).
           - **CRITICAL**: Include ONLY sentient beings (people, animals, robots).
           - **DO NOT** include locations, organizations, objects, or abstract concepts (e.g., "London", "The Police", "Love", "Engineering", "College").
           - For each character, provide:
               - Their name as it appears in the text.
               - A short role label (e.g., "protagonist", "antagonist", "friend", "mentor", "villain", "side character").
               - A concise VISUAL DESCRIPTION (e.g., "tall, red curly hair, wears a tattered cloak").
           - Represent each character as: ["Character Name", "Role", "Visual Description"].

        3. THEMES (KEYWORDS)
           - Extract 5–10 main themes of the story.
           - Each theme should be a short phrase of 1–3 words (e.g., "friendship", "betrayal", "coming of age").
           - Do NOT use generic words like "story", "book", "plot".

        4. KEY SCENES
           - Identify 3-5 key scenes that visually represent the story.
           - Each scene should be a descriptive sentence suitable for image generation.
           - Example: "The hero stands on a cliff overlooking the burning city."

        OUTPUT FORMAT (IMPORTANT):
        - Respond with EXACTLY ONE JSON OBJECT.
        - NO markdown, NO code fences, NO explanation.
        - NO trailing commas.
        - NO "..." placeholders.

        The JSON MUST follow this schema:

        {{
            "summary": "brief plot summary here",
            "entities": [
                ["Character Name 1", "Role 1", "Visual Description 1"],
                ["Character Name 2", "Role 2", "Visual Description 2"]
            ],
            "keywords": [
                "theme1",
                "theme2",
                "theme3"
            ],
            "scenes": [
                "Description of scene 1...",
                "Description of scene 2...",
                "Description of scene 3..."
            ]
        }}

        Now analyze this text (may be truncated if long):

        {text[:5000]}
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        print(f"Gemini Analysis Response: {response_text[:200]}...")  # Log first 200 chars
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        return json.loads(response_text)
        
    except Exception as e:
        import traceback
        print(f"Gemini Analysis Failed: {e}")
        traceback.print_exc()
        return {"summary": "Analysis failed.", "entities": [], "keywords": []}


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
