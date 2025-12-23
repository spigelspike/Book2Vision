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

class RateLimitController:
    """
    Manages global rate limiting for API requests.
    
    Mechanisms:
    1. Semaphore: Limits concurrent requests (e.g., max 1 at a time).
    2. Global Backoff: If any request hits a 429 (Too Many Requests), 
       ALL future requests are paused until the backoff period expires.
       This prevents spamming the API when it's already overwhelmed.
    """
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
                # Add a tiny buffer to ensure we don't wake up slightly too early
                await asyncio.sleep(wait_time + 0.1)
            else:
                break

    async def trigger_backoff(self, wait_time):
        """Updates the global backoff timestamp safely."""
        async with self.backoff_lock:
            new_target = time.time() + wait_time
            # Only extend if the new target is further in the future
            if new_target > self.global_backoff_until:
                self.global_backoff_until = new_target
                print(f"🛑 Global backoff triggered. Pausing all requests for {wait_time:.1f}s...")

# Initialize global controller
# Limit to 1 concurrent request to strictly avoid rate limits
rate_limiter = RateLimitController(max_concurrent=1)

async def generate_entity_image(entity_name, entity_role, output_dir, seed=None, style="storybook"):
    """
    Generates a circular-ready avatar image for an entity (Async).
    """
    if seed is None:
        seed = random.randint(0, 10000)
        
    prompt = (
        f"Close-up portrait of {entity_name} as {entity_role}, "
        f"centered character, facing the viewer, {style} style, "
        f"masterpiece, best quality, expressive, highly detailed, soft diffused lighting, "
        f"clean plain white background, no text, no logo, no watermark, "
        f"framed to work well as a circular avatar."
    )
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Use default model (no model param) for better reliability
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=512&height=512&nologo=true"
    
    safe_name = re.sub(r'[\\/*?:"<>|\n\r]', "_", entity_name)
    filename = f"entity_{safe_name}.jpg"
    img_path = os.path.join(output_dir, filename)
    
    return await _download_image_async(image_url, img_path, f"Entity: {entity_name}")

async def _download_image_async(url, output_path, description):
    """
    Helper to download an image asynchronously with semaphore, retries, and exponential backoff.
    """
    async with rate_limiter.semaphore:
        for attempt in range(5):
            # 1. Check global backoff before starting
            await rate_limiter.wait_if_needed()
            
            try:
                # 90s timeout for the request itself
                timeout = aiohttp.ClientTimeout(total=90)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    print(f"Starting generation for: {description} (Attempt {attempt+1})")
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            with open(output_path, 'wb') as handler:
                                handler.write(content)
                            print(f"✅ Saved: {output_path}")
                            return output_path
                        
                        elif response.status == 429:
                            # Rate limit hit!
                            # Calculate backoff: 2s, 4s, 8s, 16s, 32s + jitter
                            base_wait = (2 ** (attempt + 1))
                            jitter = random.uniform(0, 1)
                            wait_time = base_wait + jitter
                            
                            print(f"⚠️ Rate limit (429) for {description}. Triggering global backoff for {wait_time:.1f}s...")
                            
                            # Trigger global backoff so other tasks stop
                            await rate_limiter.trigger_backoff(wait_time)
                            
                            # We also wait here (redundant but safe, loop will check wait_if_needed anyway)
                            await asyncio.sleep(wait_time)
                            
                        else:
                            print(f"⚠️ Failed to download {description}: {response.status}")
                            # Retry on 5xx errors
                            if 500 <= response.status < 600:
                                wait_time = (2 ** (attempt + 1)) + random.uniform(0, 1)
                                await asyncio.sleep(wait_time)
                            else:
                                # 4xx errors (other than 429) are likely permanent
                                return None
                                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait_time = (2 ** (attempt + 1)) + random.uniform(0, 1)
                print(f"❌ Error generating {description} (Attempt {attempt+1}): {e}. Retrying in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f"❌ Unexpected error for {description}: {e}")
                return None
            finally:
                # Mandatory delay after every request (success or fail) to prevent bursts
                await asyncio.sleep(10)
                
    print(f"❌ Failed to generate {description} after all attempts.")
    return None

from src.prompts import IMAGE_PROMPT_TEMPLATE, ENTITY_PROMPT_TEMPLATE, TITLE_PROMPT_TEMPLATE, SCENE_PROMPT_TEMPLATE

async def generate_images(semantic_map, output_dir, style="manga", seed=None, title=None):
    """
    Orchestrates the asynchronous generation of all images for a book.
    
    1. Generates a Title Page.
    2. Generates Scene Illustrations (based on semantic analysis).
    3. Generates Entity Avatars (top 3 characters).
    
    Uses `aiohttp` for concurrent (but rate-limited) requests.
    """
    images = []
    
    if seed is None:
        seed = random.randint(0, 10000)
    
    print(f"Generating images with style: {style} (Seed: {seed})")
    
    tasks = []
    
    # 1. Title Page
    if title:
        prompt = TITLE_PROMPT_TEMPLATE.format(title=title, style=style)
        encoded_prompt = urllib.parse.quote(prompt)
        # Reduced resolution for reliability
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1280&height=720&nologo=true"
        
        safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
        filename = f"image_00_title_{safe_title}.jpg"
        img_path = os.path.join(output_dir, filename)
        
        tasks.append(_download_image_async(image_url, img_path, "Title Page"))

    # 2. Scene Images
    scenes = semantic_map.get("scenes", [])
    entities = semantic_map.get("entities", [])
    
    # Build Character Context
    char_context = []
    for ent in entities:
        name = ent[0] if len(ent) > 0 else "Unknown"
        desc = ent[2] if len(ent) > 2 else ""
        if desc:
            char_context.append(f"{name} ({desc})")
        else:
            char_context.append(name)
    
    context_str = ", ".join(char_context)
    
    for i, scene_desc in enumerate(scenes):
        prompt = SCENE_PROMPT_TEMPLATE.format(
            scene_description=scene_desc, 
            character_context=context_str,
            style=style
        )
        encoded_prompt = urllib.parse.quote(prompt)
        # Reduced resolution
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed+200+i}&width=1280&height=720&nologo=true"
        
        filename = f"image_01_scene_{i+1:02d}.jpg"
        img_path = os.path.join(output_dir, filename)
        
        tasks.append(_download_image_async(image_url, img_path, f"Scene {i+1}"))

    # 3. Entity Images
    top_entities = entities[:3]
    for i, entity in enumerate(top_entities):
        if isinstance(entity, list) and len(entity) >= 2:
            name, role = entity[0], entity[1]
        elif isinstance(entity, tuple) and len(entity) >= 2:
            name, role = entity[0], entity[1]
        else:
            name = str(entity)
            role = "Character"
        
        prompt = ENTITY_PROMPT_TEMPLATE.format(name=name, role=role, style=style)
        encoded_prompt = urllib.parse.quote(prompt)
        # Reduced resolution
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed+i+1}&width=1280&height=720&nologo=true"
        
        safe_name = "".join([c if c.isalnum() else "_" for c in name])[:30]
        filename = f"image_02_entity_{safe_name}.jpg"
        img_path = os.path.join(output_dir, filename)
        
        tasks.append(_download_image_async(image_url, img_path, f"Entity: {name}"))

    # Execute all tasks
    print(f"Starting async generation of {len(tasks)} images...")
    results = await asyncio.gather(*tasks)
    
    # Filter out None results and sort
    images = [img for img in results if img]
    images.sort()
    
    return images
