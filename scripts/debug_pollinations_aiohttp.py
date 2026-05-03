import aiohttp
import asyncio
import urllib.parse
import time

SCENE_PROMPT_TEMPLATE = """
Cinematic illustration of a key scene: {scene_description},
Context: {character_context}
{style} style, highly detailed, dramatic composition, dynamic angle, 
visual storytelling, 8k resolution, 16:9 aspect ratio, 
no text, no watermark, masterpiece.
"""

async def test_pollinations_complex():
    print("Testing Pollinations with complex prompt...")
    
    scene_desc = "A beautiful sunset over a calm ocean."
    character_context = "Hero (Protagonist)"
    style = "manga"
    
    prompt = SCENE_PROMPT_TEMPLATE.format(
        scene_description=scene_desc, 
        character_context=character_context,
        style=style
    )
    
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed=42&width=1920&height=1080&model=flux&nologo=true&enhance=true"
    
    print(f"URL: {url}")
    
    start = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print("Session created. Sending request...")
            async with session.get(url) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    content = await response.read()
                    print(f"Success! Time: {time.time() - start:.2f}s")
                    with open("debug_pollinations_complex.jpg", "wb") as f:
                        f.write(content)
                else:
                    print(f"Failed: {response.status}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pollinations_complex())
