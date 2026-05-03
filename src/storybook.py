"""
Book2Vision - 2D Illustrated Storybook Module
Generates visually consistent 2D illustrations across all pages of a book.

Features:
- Character Bible: Maintains consistent character appearances
- Scene Memory: Tracks locations, time, and environment elements
- Page-by-Page Generation: Creates illustrations matching story text
- Style Lock: Enforces 2D hand-drawn/painted aesthetic
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from google import genai
from src.config import GEMINI_API_KEY
from src.visuals import generate_images, _generate_image_with_deapi, _download_image_async


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CharacterBible:
    """Stores consistent character appearance for visual generation."""
    name: str
    age: str = ""
    gender: str = ""
    physical_description: str = ""  # Hair, eyes, skin, height, build
    clothing: str = ""
    distinguishing_features: str = ""  # Scars, accessories, unique traits
    personality_visual_cues: str = ""  # Expression tendencies, posture
    
    def to_prompt(self) -> str:
        """Convert to prompt-friendly format."""
        parts = [f"CHARACTER: {self.name}"]
        if self.age:
            parts.append(f"Age: {self.age}")
        if self.gender:
            parts.append(f"Gender: {self.gender}")
        if self.physical_description:
            parts.append(f"Appearance: {self.physical_description}")
        if self.clothing:
            parts.append(f"Clothing: {self.clothing}")
        if self.distinguishing_features:
            parts.append(f"Distinctive: {self.distinguishing_features}")
        return " | ".join(parts)


@dataclass
class SceneMemory:
    """Tracks scene details for consistency."""
    scene_id: str
    location: str = ""
    time_of_day: str = ""  # morning, afternoon, evening, night
    weather: str = ""
    environment_elements: List[str] = field(default_factory=list)
    mood: str = ""  # happy, tense, mysterious, etc.
    
    def to_prompt(self) -> str:
        """Convert to prompt-friendly format."""
        parts = [f"SCENE {self.scene_id}"]
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.time_of_day:
            parts.append(f"Time: {self.time_of_day}")
        if self.weather:
            parts.append(f"Weather: {self.weather}")
        if self.environment_elements:
            parts.append(f"Elements: {', '.join(self.environment_elements)}")
        if self.mood:
            parts.append(f"Mood: {self.mood}")
        return " | ".join(parts)


@dataclass
class WorldBible:
    """Master document for visual consistency."""
    genre: str = "children's fantasy"
    age_range: str = "4-8 years"
    art_style: str = "watercolor illustration"
    color_palette: str = "warm, soft pastels"
    lighting: str = "flat, painterly"
    perspective: str = "simple storybook illustration"
    
    # Collections
    characters: Dict[str, CharacterBible] = field(default_factory=dict)
    scenes: Dict[str, SceneMemory] = field(default_factory=dict)
    
    # Style rules
    banned_styles: List[str] = field(default_factory=lambda: [
        "3D render", "CGI", "Pixar", "Unreal Engine", 
        "anime", "manga", "photorealism", "realistic photo",
        "depth simulation", "3D lighting"
    ])


@dataclass
class StoryPage:
    """Single page of the storybook."""
    page_number: int
    text: str
    characters_present: List[str] = field(default_factory=list)
    scene_id: str = ""
    image_path: Optional[str] = None
    prompt_used: str = ""


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

async def extract_character_bible(book_text: str, existing_entities: List[dict] = None) -> Dict[str, CharacterBible]:
    """
    Extract detailed character descriptions from book text.
    Uses Gemini to analyze and create consistent character bibles.
    """
    print(" Extracting character bible from book text...")
    
    prompt = f"""Analyze this story and extract detailed character descriptions for illustration.

For each main character, provide:
1. NAME: Full name used in story
2. AGE: Approximate age or age description
3. GENDER: Male/Female/Other
4. PHYSICAL: Hair color/style, eye color, skin tone, height, body type
5. CLOTHING: Default outfit worn in the story
6. DISTINCTIVE: Unique features like scars, glasses, accessories

Output as JSON array:
[
  {{
    "name": "Character Name",
    "age": "age description",
    "gender": "gender",
    "physical_description": "detailed physical appearance",
    "clothing": "typical outfit",
    "distinguishing_features": "unique visual traits"
  }}
]

STORY TEXT:
{book_text[:8000]}

Return ONLY valid JSON array, no other text.
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        
        # Parse JSON response
        json_text = response.text.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("```")[1]
            if json_text.startswith("json"):
                json_text = json_text[4:]
        
        characters_data = json.loads(json_text)
        
        characters = {}
        for char_data in characters_data:
            name = char_data.get("name", "Unknown")
            characters[name] = CharacterBible(
                name=name,
                age=char_data.get("age", ""),
                gender=char_data.get("gender", ""),
                physical_description=char_data.get("physical_description", ""),
                clothing=char_data.get("clothing", ""),
                distinguishing_features=char_data.get("distinguishing_features", "")
            )
        
        print(f" Extracted {len(characters)} character bibles")
        return characters
        
    except Exception as e:
        print(f" Character extraction failed: {e}")
        # Fallback: use existing entities if provided
        if existing_entities:
            characters = {}
            for entity in existing_entities:
                name = entity.get("name", "Character")
                characters[name] = CharacterBible(
                    name=name,
                    physical_description=entity.get("description", ""),
                )
            return characters
        return {}


async def extract_scenes_and_pages(book_text: str) -> Tuple[Dict[str, SceneMemory], List[StoryPage]]:
    """
    Split book into pages and identify scene information.
    """
    print(" Extracting scenes and splitting into pages...")
    
    prompt = f"""Analyze this story and:
1. Identify distinct scenes (location/time changes)
2. Split into logical "pages" for an illustrated storybook (3-5 sentences each)
3. Note which characters appear on each page

Output as JSON:
{{
  "scenes": [
    {{
      "scene_id": "S1",
      "location": "where this scene takes place",
      "time_of_day": "morning/afternoon/evening/night",
      "mood": "emotional tone"
    }}
  ],
  "pages": [
    {{
      "page_number": 1,
      "text": "the text for this page",
      "characters_present": ["Character Name 1", "Character Name 2"],
      "scene_id": "S1"
    }}
  ]
}}

STORY TEXT:
{book_text[:10000]}

Return ONLY valid JSON, no other text.
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        
        json_text = response.text.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("```")[1]
            if json_text.startswith("json"):
                json_text = json_text[4:]
        
        data = json.loads(json_text)
        
        # Create scene memories
        scenes = {}
        for scene_data in data.get("scenes", []):
            scene_id = scene_data.get("scene_id", "S1")
            scenes[scene_id] = SceneMemory(
                scene_id=scene_id,
                location=scene_data.get("location", ""),
                time_of_day=scene_data.get("time_of_day", ""),
                mood=scene_data.get("mood", "")
            )
        
        # Create pages
        pages = []
        for page_data in data.get("pages", []):
            pages.append(StoryPage(
                page_number=page_data.get("page_number", len(pages) + 1),
                text=page_data.get("text", ""),
                characters_present=page_data.get("characters_present", []),
                scene_id=page_data.get("scene_id", "S1")
            ))
        
        print(f" Extracted {len(scenes)} scenes and {len(pages)} pages")
        return scenes, pages
        
    except Exception as e:
        print(f" Scene extraction failed: {e}")
        # Fallback: split by paragraphs
        paragraphs = [p.strip() for p in book_text.split("\n\n") if p.strip()]
        pages = []
        for i, para in enumerate(paragraphs[:20], 1):  # Max 20 pages
            pages.append(StoryPage(page_number=i, text=para, scene_id="S1"))
        scenes = {"S1": SceneMemory(scene_id="S1", location="story setting")}
        return scenes, pages


# ============================================================================
# PROMPT GENERATION
# ============================================================================

def build_storybook_prompt(
    page: StoryPage,
    world: WorldBible,
    characters: Dict[str, CharacterBible],
    scene: Optional[SceneMemory] = None
) -> str:
    """
    Build a comprehensive prompt for generating a single storybook page illustration.
    Enforces 2D style and character consistency.
    """
    
    # Build banned styles string
    banned = ", ".join(world.banned_styles)
    
    # Build character descriptions for characters in this scene
    char_descriptions = []
    for char_name in page.characters_present:
        if char_name in characters:
            char_descriptions.append(characters[char_name].to_prompt())
    
    char_section = "\n".join(char_descriptions) if char_descriptions else "Generic story characters"
    
    # Scene description
    scene_section = scene.to_prompt() if scene else "Story scene"
    
    prompt = f"""2D HAND-DRAWN STORYBOOK ILLUSTRATION

STYLE REQUIREMENTS (MANDATORY):
- Art medium: {world.art_style}
- Color palette: {world.color_palette}
- Lighting: {world.lighting}
- Visual style: Flat 2D illustration, hand-painted look
- Perspective: {world.perspective}
- Genre: {world.genre}
- Audience: {world.age_range}

BANNED STYLES (DO NOT USE): {banned}

CHARACTERS IN THIS SCENE:
{char_section}

SCENE CONTEXT:
{scene_section}

PAGE {page.page_number} - ILLUSTRATION TEXT:
"{page.text}"

COMPOSITION RULES:
- Clear focal point on main action described
- Balanced, child-friendly composition
- Characters must match their bible descriptions exactly
- Show emotion through facial expressions and body language
- No text or speech bubbles in the image
- Print-ready storybook quality

Generate a beautiful 2D illustrated storybook page matching this description."""

    return prompt


# ============================================================================
# GENERATION FUNCTIONS
# ============================================================================

async def generate_storybook_page(
    page: StoryPage,
    world: WorldBible,
    characters: Dict[str, CharacterBible],
    scenes: Dict[str, SceneMemory],
    output_dir: str,
    provider: str = "pollinations"
) -> StoryPage:
    """
    Generate illustration for a single storybook page.
    """
    import urllib.parse
    import aiohttp
    import os
    
    print(f" Generating illustration for page {page.page_number}...")
    
    scene = scenes.get(page.scene_id)
    prompt = build_storybook_prompt(page, world, characters, scene)
    page.prompt_used = prompt
    
    # Generate image
    output_path = f"{output_dir}/storybook_page_{page.page_number:02d}.jpg"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        if provider == "deapi":
            # Use deAPI through async helper
            async with aiohttp.ClientSession() as session:
                result = await _generate_image_with_deapi(session, prompt, output_path, f"Page {page.page_number}")
                page.image_path = result
        else:
            # Use Pollinations.ai
            encoded_prompt = urllib.parse.quote(prompt[:500])  # Limit prompt length for URL
            seed = page.page_number * 1000  # Consistent seed per page
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=800&seed={seed}&nologo=true"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            async with aiohttp.ClientSession(headers=headers) as session:
                result = await _download_image_async(session, image_url, output_path, f"Page {page.page_number}")
                page.image_path = result
        
        if page.image_path:
            print(f" Page {page.page_number} illustration saved: {page.image_path}")
        
    except Exception as e:
        print(f" Page {page.page_number} generation failed: {e}")
        page.image_path = None
    
    return page


async def generate_full_storybook(
    book_text: str,
    output_dir: str,
    world_config: Optional[dict] = None,
    existing_entities: List[dict] = None,
    provider: str = "pollinations",
    max_pages: int = 10
) -> Tuple[WorldBible, List[StoryPage]]:
    """
    Generate a complete illustrated storybook from book text.
    
    Args:
        book_text: The full story text
        output_dir: Directory to save generated images
        world_config: Optional world bible configuration
        existing_entities: Optional pre-extracted character entities
        provider: Image generation provider (pollinations/deapi)
        max_pages: Maximum number of pages to generate
    
    Returns:
        Tuple of (WorldBible, List[StoryPage])
    """
    print("=" * 60)
    print(" STORYBOOK GENERATION STARTED")
    print("=" * 60)
    
    # Create world bible
    world = WorldBible()
    if world_config:
        world.genre = world_config.get("genre", world.genre)
        world.age_range = world_config.get("age_range", world.age_range)
        world.art_style = world_config.get("art_style", world.art_style)
        world.color_palette = world_config.get("color_palette", world.color_palette)
    
    # Step 1: Extract character bibles
    characters = await extract_character_bible(book_text, existing_entities)
    world.characters = characters
    
    # Step 2: Extract scenes and split into pages
    scenes, pages = await extract_scenes_and_pages(book_text)
    world.scenes = scenes
    
    # Limit pages
    if len(pages) > max_pages:
        print(f" Limiting to {max_pages} pages (from {len(pages)})")
        pages = pages[:max_pages]
    
    # Step 3: Generate illustrations for each page
    print(f"\n Generating {len(pages)} page illustrations...")
    
    generated_pages = []
    for page in pages:
        result = await generate_storybook_page(
            page, world, characters, scenes, output_dir, provider
        )
        generated_pages.append(result)
        
        # Small delay between generations to avoid rate limits
        await asyncio.sleep(1)
    
    successful = sum(1 for p in generated_pages if p.image_path)
    print("=" * 60)
    print(f" STORYBOOK COMPLETE: {successful}/{len(generated_pages)} pages generated")
    print("=" * 60)
    
    return world, generated_pages


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def world_bible_to_json(world: WorldBible) -> dict:
    """Convert WorldBible to JSON-serializable dict."""
    return {
        "genre": world.genre,
        "age_range": world.age_range,
        "art_style": world.art_style,
        "color_palette": world.color_palette,
        "lighting": world.lighting,
        "perspective": world.perspective,
        "banned_styles": world.banned_styles,
        "characters": {name: asdict(char) for name, char in world.characters.items()},
        "scenes": {sid: asdict(scene) for sid, scene in world.scenes.items()}
    }


def pages_to_json(pages: List[StoryPage]) -> List[dict]:
    """Convert pages list to JSON-serializable format."""
    return [asdict(page) for page in pages]
