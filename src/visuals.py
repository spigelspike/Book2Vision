import aiohttp
import asyncio
import os
import urllib.parse
import re
import random
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting configuration
MAX_CONCURRENT_REQUESTS = 4  # Increased to speed up generation
MAX_RETRY_ATTEMPTS = 3  # Reduced retries to fail faster
BASE_RETRY_DELAY_SECONDS = 2
INTER_REQUEST_DELAY_SECONDS = 1

# Common headers to avoid being blocked
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
}

class RateLimitController:
    def __init__(self, max_concurrent=2):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.global_backoff_until = 0.0
        self.backoff_lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Checks if we are in a global backoff period and waits if so."""
        while True:
            now = time.time()
            if now < self.global_backoff_until:
                wait_time = self.global_backoff_until - now
                await asyncio.sleep(wait_time + 0.1)
            else:
                break

    async def trigger_backoff(self, wait_time):
        """Updates the global backoff timestamp safely."""
        async with self.backoff_lock:
            new_target = time.time() + wait_time
            if new_target > self.global_backoff_until:
                self.global_backoff_until = new_target
                print(f" Global backoff triggered. Pausing all requests for {wait_time:.1f}s...")

# Initialize global controller
rate_limiter = RateLimitController(max_concurrent=MAX_CONCURRENT_REQUESTS)

async def generate_entity_image(entity_name, entity_role, output_dir, seed=None):
    """
    Generates a circular-ready avatar image for an entity (Async).
    Uses DeAPI (Flux1schnell) for best quality, falls back to Pollinations.
    """
    if seed is None:
        seed = random.randint(0, 10000)
        
    from src.prompts import ENTITY_PROMPT_TEMPLATE
    # Use species if available (not passed here, so generic)
    prompt = ENTITY_PROMPT_TEMPLATE.format(name=entity_name, role=entity_role, species="Character", style="digital art")
    
    safe_name = re.sub(r'[\\/*?:"<>|\n\r]', "_", entity_name)
    filename = f"entity_{safe_name}.jpg"
    img_path = os.path.join(output_dir, filename)
    
    # Try DeAPI first
    api_key = os.getenv("DEAPI_API_KEY")
    if api_key:
        async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session:
            result = await _generate_image_with_deapi(session, prompt, img_path, f"Entity: {entity_name}", width=1024, height=1024)
            if result:
                return result
    
    # Fallback to Pollinations with a simpler, shorter prompt to avoid 404s
    print(f" Falling back to Pollinations for {entity_name}...")
    # Keep prompt short to avoid URL length issues
    short_prompt = f"character portrait of {entity_name}, {entity_role}, digital art, detailed face, studio lighting, bokeh background"
    encoded_prompt = urllib.parse.quote(short_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1024&height=1024&model=flux&nologo=true"
    
    async with aiohttp.ClientSession() as session:
        return await _download_image_async(session, image_url, img_path, f"Entity: {entity_name}")

async def _download_image_async(session, url, output_path, description):
    """
    Helper to download an image asynchronously with semaphore, retries, and exponential backoff.
    Uses a shared session.
    """
    async with rate_limiter.semaphore:
        for attempt in range(MAX_RETRY_ATTEMPTS):
            await rate_limiter.wait_if_needed()
            
            try:
                # 30s timeout for the request itself
                timeout = aiohttp.ClientTimeout(total=45) # Increased timeout
                print(f" Starting download for: {description} (Attempt {attempt+1})")
                
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Verify content is actually an image
                        if len(content) < 1000:
                            print(f" Warning: Image content too small for {description}")
                            continue
                            
                        with open(output_path, 'wb') as handler:
                            handler.write(content)
                        print(f" Saved: {output_path}")
                        return output_path
                    
                    elif response.status == 429:
                        base_wait = (2 ** (attempt + 1))
                        jitter = random.uniform(0, 1)
                        wait_time = base_wait + jitter
                        print(f" Rate limit (429) for {description}. Backoff {wait_time:.1f}s...")
                        await rate_limiter.trigger_backoff(wait_time)
                        await asyncio.sleep(wait_time)
                        
                    elif response.status >= 500:
                        print(f" Server error {response.status} for {description}. Retrying...")
                        await asyncio.sleep(2)
                        
                    else:
                        print(f" Failed to download {description}: {response.status}")
                        return None
                                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait_time = (2 ** (attempt + 1))
                print(f" Error generating {description} (Attempt {attempt+1}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f" Unexpected error for {description}: {e}")
                return None
        
        if attempt < (MAX_RETRY_ATTEMPTS - 1):
            await asyncio.sleep(INTER_REQUEST_DELAY_SECONDS)
                
    print(f" Failed to generate {description} after all attempts.")
    return None

from src.prompts import IMAGE_PROMPT_TEMPLATE, ENTITY_PROMPT_TEMPLATE, TITLE_PROMPT_TEMPLATE, SCENE_PROMPT_TEMPLATE, NEGATIVE_PROMPT, COVER_PROMPT_TEMPLATE

async def _generate_image_with_deapi(session, prompt, output_path, description, width=1920, height=1080):
    """Helper to generate a single image using deAPI with shared session."""
    api_key = os.getenv("DEAPI_API_KEY")
    if not api_key:
        print(f" DEAPI_API_KEY missing for {description}")
        return None

    try:
        # Use clean headers for deAPI - do NOT merge DEFAULT_HEADERS (browser Accept header conflicts)
        api_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "model": "Flux1schnell",
            "width": width,
            "height": height,
            "steps": 6,
            "guidance": 0,
            "seed": random.randint(1, 999999999),
            "negative_prompt": NEGATIVE_PROMPT
        }
        
        print(f" deAPI Request (v2): {description}")
        async with session.post(
            "https://api.deapi.ai/api/v2/images/generations",
            headers=api_headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                error_body = await response.text()
                print(f" deAPI Request Failed: {response.status}")
                print(f"Response: {error_body}")
                return None
            
            data = await response.json()
            request_id = data.get("data", {}).get("request_id")
            
            if not request_id:
                print(f" deAPI: No request_id returned for {description}")
                return None
            
            print(f" deAPI Job ID: {request_id}")
        
        # Poll using v2 jobs endpoint
        for _ in range(30):
            await asyncio.sleep(2)
            async with session.get(
                f"https://api.deapi.ai/api/v2/jobs/{request_id}",
                headers=api_headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as status_res:
                if status_res.status != 200: continue
                
                status_data = await status_res.json()
                status = status_data.get("data", {}).get("status")
                result_url = status_data.get("data", {}).get("result_url")
                
                if status == "done" and result_url:
                    # Download the generated image
                    async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=60)) as img_res:
                        if img_res.status == 200:
                            content = await img_res.read()
                            with open(output_path, 'wb') as f:
                                f.write(content)
                            print(f" deAPI Saved: {output_path}")
                            return output_path
                    break
                elif status == "error":
                    print(f" deAPI Generation Failed: {description}")
                    return None
    except Exception as e:
        print(f" deAPI Error for {description}: {e}")
        return None
    return None

# ----------------------------------------------------------------------------
# CHARACTER PORTRAIT SYSTEM
# ----------------------------------------------------------------------------

# Character visual cache for consistency
_character_visual_cache = {}

def get_character_seed(name: str) -> int:
    """Generate a consistent seed for a character based on their name."""
    return abs(hash(name)) % (2**31)

def get_character_color_palette(role: str) -> str:
    """Generate color palette suggestion based on character role."""
    palettes = {
        "protagonist": "warm tones, gold highlights, heroic blue accents",
        "antagonist": "dark purples, crimson accents, cold shadows",
        "mentor": "wise silvers, deep blues, warm amber",
        "ally": "friendly greens, warm yellows, soft earth tones",
        "love interest": "romantic pinks, soft purples, warm highlights",
        "comic relief": "bright oranges, playful yellows, vibrant accents",
        "mysterious": "deep indigo, silver highlights, misty grays",
        "default": "balanced natural tones, complementary accents"
    }
    role_lower = role.lower()
    for key in palettes:
        if key in role_lower:
            return palettes[key]
    return palettes["default"]

async def generate_character_portrait(
    name: str,
    role: str,
    physical_description: str,
    outfit: str,
    signature_prop: str,
    output_dir: str,
    style: str = "anime",
    genre: str = "fantasy",
    pose_type: str = "confident standing",
    expression: str = "determined"
) -> str:
    """
    Generates a full-body character portrait with consistency anchors.
    """
    from src.prompts import CHARACTER_PORTRAIT_PROMPT
    
    # Get consistent seed for this character
    character_seed = get_character_seed(name)
    color_palette = get_character_color_palette(role)
    
    # Determine background based on genre
    background_colors = {
        "fantasy": "soft ethereal gradient",
        "sci-fi": "tech-blue to dark gray gradient",
        "horror": "dark misty gradient",
        "romance": "warm sunset gradient",
        "thriller": "noir shadows gradient",
        "default": "neutral studio gray"
    }
    background = background_colors.get(genre.lower(), background_colors["default"])
    
    # Build the prompt
    prompt = CHARACTER_PORTRAIT_PROMPT.format(
        name=name,
        role=role,
        genre=genre,
        physical_description=physical_description,
        outfit=outfit,
        signature_prop=signature_prop if signature_prop and signature_prop.lower() != "none" else "no special items",
        style=style,
        color_palette=color_palette,
        character_seed=character_seed,
        pose_type=pose_type,
        expression=expression,
        background_color=background
    )
    
    # Cache the visual description for use in scene generation
    _character_visual_cache[name] = {
        "seed": character_seed,
        "physical": physical_description,
        "outfit": outfit,
        "prop": signature_prop,
        "color_palette": color_palette,
        "prompt_snippet": f"{name}: {physical_description}, wearing {outfit}"
    }
    
    # Generate filename
    safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
    filename = f"portrait_{safe_name}.jpg"
    img_path = os.path.join(output_dir, filename)
    
    # Use Pollinations for character portraits
    headers = DEFAULT_HEADERS.copy()
    async with aiohttp.ClientSession(headers=headers) as session:
        print(f" Generating portrait for {name} with Pollinations...")
        encoded_prompt = urllib.parse.quote(prompt[:1000])  # URL length limit
        seed = character_seed
        
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=768&height=1024&model=flux&nologo=true"
        return await _download_image_async(session, image_url, img_path, f"Portrait: {name}")

async def generate_character_sheet(
    name: str,
    role: str,
    physical_description: str,
    outfit: str,
    signature_prop: str,
    output_dir: str,
    style: str = "anime"
) -> str:
    """
    Generates a multi-view character reference sheet.
    """
    from src.prompts import CHARACTER_SHEET_PROMPT
    
    prompt = CHARACTER_SHEET_PROMPT.format(
        name=name,
        role=role,
        physical_description=physical_description,
        outfit=outfit,
        signature_prop=signature_prop if signature_prop and signature_prop.lower() != "none" else "no accessories",
        style=style
    )
    
    safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
    filename = f"sheet_{safe_name}.jpg"
    img_path = os.path.join(output_dir, filename)
    
    headers = DEFAULT_HEADERS.copy()
    async with aiohttp.ClientSession(headers=headers) as session:
        print(f" Generating sheet for {name} with Pollinations...")
        encoded_prompt = urllib.parse.quote(prompt[:1000])
        seed = get_character_seed(name)
            
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1920&height=1080&model=flux&nologo=true"
        return await _download_image_async(session, image_url, img_path, f"Sheet: {name}")

async def generate_all_character_portraits(semantic_map: dict, output_dir: str, style: str = "anime", genre: str = "fantasy") -> list:
    """
    Generates portraits for all characters in the semantic map.
    """
    entities = semantic_map.get("entities", [])
    if not entities:
        print(" No entities found for portrait generation")
        return []
    
    portraits = []
    
    for entity in entities:
        # Parse entity data (supports both 3-item and 5-item formats)
        if isinstance(entity, list):
            if len(entity) >= 5:
                name, role, physical, outfit, prop = entity[0], entity[1], entity[2], entity[3], entity[4]
            elif len(entity) >= 3:
                name, role, physical = entity[0], entity[1], entity[2]
                outfit = "appropriate attire for their role"
                prop = "none"
            elif len(entity) >= 2:
                name, role = entity[0], entity[1]
                physical = "distinctive appearance"
                outfit = "appropriate attire"
                prop = "none"
            else:
                continue
        else:
            continue
        
        portrait_path = await generate_character_portrait(
            name=name,
            role=role,
            physical_description=physical,
            outfit=outfit,
            signature_prop=prop,
            output_dir=output_dir,
            style=style,
            genre=genre
        )
        
        if portrait_path:
            portraits.append(portrait_path)
    
    print(f" Generated {len(portraits)} character portraits")
    return portraits

def get_cached_character_visuals() -> dict:
    """Returns the cached character visual descriptions for scene consistency."""
    return _character_visual_cache.copy()

async def _generate_entity_with_fallback(session, prompt, img_path, description, seed, model="flux"):
    """
    Tries to generate with deAPI, falls back to Pollinations if it fails.
    """
    # Try deAPI first
    result = await _generate_image_with_deapi(session, prompt, img_path, description, width=1024, height=1024)
    if result:
        return result
    
    # Fallback to Pollinations
    print(f" Falling back to Pollinations for {description}...")
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1024&height=1024&model={model}&nologo=true"
    
    return await _download_image_async(session, image_url, img_path, description)

async def generate_images(semantic_map, output_dir, style="manga", seed=None, title=None, include_entities=True):
    """
    Generates images based on semantic analysis using Pollinations.ai (Flux) for scenes and deAPI for entities.
    """
    has_deapi = bool(os.getenv("DEAPI_API_KEY"))
    scene_provider = "pollinations"  # Hardcoded per user request
    entity_provider = "deapi" if has_deapi else "pollinations"
    model = "flux"  # Flux Schnell - best quality/speed balance
    print("="*50)
    print(f" generate_images() STARTED")
    print(f"Scene Provider: {scene_provider}")
    print(f"Entity Provider: {entity_provider}")
    print(f"Model: {model}")
    print(f"Style: {style}")
    print(f"Title: {title}")
    print("="*50)
    
    # Import prompt templates
    from src.prompts import TITLE_PROMPT_TEMPLATE, SCENE_PROMPT_TEMPLATE
    
    images = []
    
    if seed is None:
        seed = random.randint(0, 10000)
    
    print(f"Generating images with style: {style} (Seed: {seed})")
    
    # Create a single session for all requests in this batch
    headers = DEFAULT_HEADERS.copy()
        
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        
        # 1. Title Page
        if title:
            prompt = TITLE_PROMPT_TEMPLATE.format(title=title, style=style)
            safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
            filename = f"image_00_title_{safe_title}.jpg"
            img_path = os.path.join(output_dir, filename)
            
            if scene_provider == "deapi":
                 tasks.append(_generate_image_with_deapi(session, prompt, img_path, "Title Page"))
            else:
                encoded_prompt = urllib.parse.quote(prompt)
                # Updated to use turbo model with 3:2 aspect ratio (less distortion)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1536&height=1024&model={model}&nologo=true"
                tasks.append(_download_image_async(session, image_url, img_path, "Title Page"))

        # 2. Scene Images
        scenes = semantic_map.get("scenes", [])
        entities = semantic_map.get("entities", [])
        
        # Prepare character context with outfits and props
        context_str = ""
        if entities:
            char_details = []
            for e in entities:
                # Handle both old format (3 items) and new format (5 items)
                if len(e) >= 5:
                    name, role, desc, outfit, prop = e[0], e[1], e[2], e[3], e[4]
                    detail = f"{name} ({role}): {desc}. Outfit: {outfit}. Prop: {prop}"
                elif len(e) >= 3:
                    name, role, desc = e[0], e[1], e[2]
                    detail = f"{name} ({role}): {desc}"
                else:
                    detail = str(e)
                char_details.append(detail)
            context_str = "; ".join(char_details)
        
        # Extract story summary for context
        story_summary = semantic_map.get("summary", "A story")
        
        # Dynamic Camera Angles for Variety
        CAMERA_ANGLES = [
            "Wide angle establishing shot",
            "Low angle looking up, dramatic perspective",
            "High angle looking down, bird's eye view",
            "Over-the-shoulder action shot",
            "Close-up on key action details",
            "Dutch angle, tilted frame for tension",
            "Cinematic wide screen composition",
            "Dynamic action angle with motion blur"
        ]

        for i, scene_item in enumerate(scenes):
            if isinstance(scene_item, dict):
                scene_desc = scene_item.get("description", "")
                emotion = scene_item.get("emotion", "")
                mood = scene_item.get("mood", "")
                environment = scene_item.get("environment", "")
            else:
                scene_desc = str(scene_item)
                emotion = ""
                mood = ""
                environment = ""
            
            # Select random camera angle
            camera_angle = random.choice(CAMERA_ANGLES)

            # Enhance scene description with emotional context
            if emotion or mood:
                emotional_context = []
                if emotion:
                    emotional_context.append(f"emotional tone: {emotion}")
                if mood:
                    emotional_context.append(f"atmosphere: {mood}")
                scene_desc_enhanced = f"{scene_desc}, {', '.join(emotional_context)}"
            else:
                scene_desc_enhanced = scene_desc
                
            prompt = SCENE_PROMPT_TEMPLATE.format(
                scene_description=scene_desc_enhanced, 
                story_summary=story_summary,
                character_context=context_str,
                environment_context=environment,
                camera_angle=camera_angle,
                style=style
            )
            
            filename = f"image_01_scene_{i+1:02d}.jpg"
            img_path = os.path.join(output_dir, filename)
            
            if scene_provider == "deapi":
                tasks.append(_generate_image_with_deapi(session, prompt, img_path, f"Scene {i+1}"))
            else:
                encoded_prompt = urllib.parse.quote(prompt)
                # Updated dimensions for better quality (3:2 aspect ratio)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed+200+i}&width=1536&height=1024&model={model}&nologo=true"
                tasks.append(_download_image_async(session, image_url, img_path, f"Scene {i+1}"))

        # 3. Entity Images
        top_entities = []
        if include_entities:
            top_entities = entities[:3]
        for i, entity in enumerate(top_entities):
            species = "Character"
            if isinstance(entity, list) and len(entity) >= 3:
                name, role, species = entity[0], entity[1], entity[2]
            elif isinstance(entity, list) and len(entity) >= 2:
                name, role = entity[0], entity[1]
            elif isinstance(entity, tuple) and len(entity) >= 2:
                name, role = entity[0], entity[1]
            else:
                name = str(entity)
                role = "Character"
            
            prompt = ENTITY_PROMPT_TEMPLATE.format(name=name, role=role, species=species, style=style)
            safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
            filename = f"image_02_entity_{safe_name}.jpg"
            img_path = os.path.join(output_dir, filename)
            
            if entity_provider == "deapi":
                 tasks.append(_generate_entity_with_fallback(session, prompt, img_path, f"Entity: {name}", seed=seed+i+1, model=model))
            else:
                encoded_prompt = urllib.parse.quote(prompt)
                # Updated to use authenticated gen.pollinations.ai endpoint with selected model
                # Removed enhance and negative params to fix 400 error
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed+i+1}&width=1024&height=1024&model={model}&nologo=true"
                tasks.append(_download_image_async(session, image_url, img_path, f"Entity: {name}"))

        # Execute all tasks
        print(f"Starting async generation of {len(tasks)} images...")
        results = await asyncio.gather(*tasks)
        
        images = [img for img in results if img]
        images.sort()
        
        return images

async def generate_poster_with_deapi(title, author, output_dir, style="cinematic", theme="", characters=None):
    """
    Generates a book cover using deAPI (Flux1schnell model), 
    with fallback to Pollinations.
    """
    # Create session for this operation
    async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session:
        api_key = os.getenv("DEAPI_API_KEY")
        if not api_key:
            print(" DEAPI_API_KEY not found for poster generation.")
            return await _generate_poster_fallback(session, title, author, output_dir, style, theme)
        
        # Build context string for characters
        char_context = ""
        if characters:
            clean_chars = []
            for c in characters[:3]:
                if isinstance(c, (list, tuple)) and len(c) > 0:
                    clean_chars.append(str(c[0]))
                else:
                    clean_chars.append(str(c))
            if clean_chars:
                char_context = f"Featuring {', '.join(clean_chars)}. "
        
        theme_context = ""
        if theme and len(theme) > 20:
            theme_context = f"Themes: {theme[:200]}. "
        
        prompt = COVER_PROMPT_TEMPLATE.format(
            title=title,
            author=author,
            theme_context=theme_context,
            char_context=char_context,
            style=style
        )
        
        seed = abs(hash(title)) % (2**31)
        print(f" Generating cover with deAPI (Flux1schnell) for: {title}")
        
        try:
            # Step 1: Request image generation via v2 endpoint
            api_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "model": "Flux1schnell",
                "width": 800,
                "height": 1280,
                "seed": seed,
                "steps": 8,
                "guidance": 0,
                "negative_prompt": NEGATIVE_PROMPT
            }
            
            print(f" Sending request to deAPI (v2)...")
            async with session.post(
                "https://api.deapi.ai/api/v2/images/generations",
                headers=api_headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"deAPI request failed: {response.status} - {error_text}")
                
                data = await response.json()
                request_id = data.get("data", {}).get("request_id")
                
                if not request_id:
                    raise Exception("No request_id in deAPI response")
                
                print(f" deAPI Job ID: {request_id}")
            
            # Step 2: Poll for result using v2 jobs endpoint
            max_attempts = 30
            poll_interval = 2
            result_url = None
            
            for attempt in range(max_attempts):
                await asyncio.sleep(poll_interval)
                
                async with session.get(
                    f"https://api.deapi.ai/api/v2/jobs/{request_id}",
                    headers=api_headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as status_response:
                    if status_response.status != 200:
                        continue
                    
                    status_data = await status_response.json()
                    status = status_data.get("data", {}).get("status")
                    result_url = status_data.get("data", {}).get("result_url")
                    
                    if status == "done" and result_url:
                        print(f" Generation complete!")
                        break
                    elif status == "error":
                        raise Exception("deAPI generation failed")
            
            if not result_url:
                raise Exception("Polling timed out - no result URL")
            
            # Step 3: Download the image
            print(f" Downloading image from: {result_url}")
            async with session.get(result_url, timeout=aiohttp.ClientTimeout(total=60)) as img_response:
                if img_response.status != 200:
                    raise Exception(f"Failed to download image: {img_response.status}")
                
                image_data = await img_response.read()
                
                safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
                filename = f"cover_{safe_title}_{int(time.time())}.png"
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                
                print(f" Cover saved: {output_path}")
                return output_path
        
        except Exception as e:
            print(f" deAPI Cover Generation Failed: {e}")
            return await _generate_poster_fallback(session, title, author, output_dir, style, theme)

async def _generate_poster_fallback(session, title, author, output_dir, style, theme):
    """Fallback to Pollinations for cover generation with a detailed, relevant prompt."""
    try:
        print(" Falling back to Pollinations (Vertical Mode)...")
        # Build a rich, descriptive prompt that captures the book's essence
        theme_snippet = theme[:200] if theme else "epic storytelling"
        prompt = (
            f"Professional book cover artwork, vertical portrait composition. "
            f"Title: '{title}' by {author}. "
            f"Visual style: {style}. "
            f"Story themes: {theme_snippet}. "
            f"Cinematic lighting, dramatic composition, rich vivid colors, "
            f"masterpiece quality, trending on artstation, detailed illustration, "
            f"no text, no watermark, no border"
        )
        encoded_prompt = urllib.parse.quote(prompt)
        seed = abs(hash(title)) % (2**31)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1080&height=1920&model=flux&nologo=true"
        
        safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
        filename = f"cover_fallback_{safe_title}.jpg"
        img_path = os.path.join(output_dir, filename)
        
        return await _download_image_async(session, image_url, img_path, "Fallback Cover")
    except Exception as e:
        print(f" Pollinations Fallback Failed: {e}")
        return None



