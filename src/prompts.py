SSML_PROMPT = """
You are an expert audiobook director and SSML specialist.
Your goal is to transform the text into a deeply engaging, human-like performance.

Your task:
Rewrite the input text into SSML that sounds like a professional voice actor reading a story, not a robot reading text.

Key Guidelines for "Human" Quality:
1.  **Pacing & Rhythm:**
    -   Vary the speed. Slow down for dramatic or emotional moments (`rate="-10%"`). Speed up slightly for action or excitement (`rate="+5%"`).
    -   Use pauses effectively. Don't just pause at commas. Pause for effect before a big reveal or after a heavy statement (`<break time="300ms"/>`).
2.  **Intonation & Pitch:**
    -   Use `<prosody pitch="...">` to reflect the mood. Lower pitch slightly for serious/dark moments. Raise it for questions or excitement.
3.  **Emphasis:**
    -   Use `<emphasis level="moderate">` to highlight key words, just as a human would stress them.
4.  **Character Voices (Subtle):**
    -   If there is dialogue, try to slightly shift the pitch or rate to distinguish the speaker, but keep it subtle.

Strict Output Rules:
-   Wrap everything in `<speak>...</speak>`.
-   Use `<p>` and `<s>` tags for structure.
-   **DO NOT** add any extra words, intro, or outro.
-   **DO NOT** use markdown code blocks. Just return the raw XML string.

Input Text:
\"\"\"{text}\"\"\"
"""

IMAGE_PROMPT_TEMPLATE = """
Cinematic shot of {scene_description}, 
{style} style, masterpiece, best quality, highly detailed, sharp focus, 
dramatic lighting, visual storytelling, 8k resolution, 16:9 aspect ratio, 
no text, no watermark.
"""

ENTITY_PROMPT_TEMPLATE = """
Full body character design of {name} as {role}, 
{style} style, masterpiece, best quality, centered, expressive, 
detailed clothing, clean background, 8k resolution, no text.
"""

TITLE_PROMPT_TEMPLATE = """
Book cover art for "{title}", 
{style} style, masterpiece, best quality, elegant, captivating, 
room for title text (but no actual text), 
high quality illustration, 16:9 aspect ratio.
"""


SCENE_PROMPT_TEMPLATE = """
Cinematic illustration of a key scene: {scene_description},
Context: {character_context}
{style} style, masterpiece, best quality, highly detailed, dramatic composition, 
visual storytelling, 8k resolution, 16:9 aspect ratio, 
no text, no watermark.
"""
